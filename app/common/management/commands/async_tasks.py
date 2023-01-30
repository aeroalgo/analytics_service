import asyncio
import importlib
import json
import logging
import threading
import traceback
import aio_pika
from queue import Queue
from django.conf import settings
from django.core.cache import cache
from app.common.logger.logg import logger
from app.common.utils import method_cache_key
from django.core.management import BaseCommand
from concurrent.futures import ProcessPoolExecutor
from app.common.async_task_interface.bus import Bus
from app.common.async_task_interface.tasks import AsyncTask


class Process:
    def __init__(self, message):
        self.message = message
        self.result = None
        self.start()

    def start(self):
        try:
            task = getattr(importlib.import_module(self.message.get('task_module')), self.message.get('task_class'))
            instance = task(**self.message.get('task_data'))
            self.result = instance.process()

            if not self.result:

                # Если нет логики повторов, то считаем что произошла ошибка
                if task.task_retry_logic is None:

                    self.result = {'_exception': 'Неизвестная ошибка', '_traceback': []}

                # Иначе если есть логика повторов, делаем повтор задачи в соответствии с ней и если повторы закончились,
                # финализируем задачу и возвращаем ошибку
                elif not task.publish(retry=True):

                    # достигнут лимит повторений – финазилируем задачу
                    task.finalize()
                    self.result = {'_exception': 'Достигнут лимит повторений задачи', '_traceback': []}

        except Exception as e:
            logger.exception(e)
            self.result = {'_exception': e.__str__(), '_traceback': traceback.format_exc()}


class Command(BaseCommand, Bus):
    """
    Асинхронные методы, не возвращающие данные непосредственно пользователям.
    """

    help = 'Process async tasks'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_workers = 4
        self._sem = asyncio.Semaphore(self.max_workers)

    def handle(self, *args, **kwargs):
        logger.info('asynchronous task started')
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.connect_consumer())
        self.loop.run_forever()

    async def connect_consumer(self):
        connection = await aio_pika.connect(settings.RABBITMQ_URL)
        try:
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)
                queue = await channel.declare_queue(self.QUEUE_TPL['TASKS'].format(ns=self.bus_ns),
                                                    durable=True)
                serializer = lambda x: json.loads(x.decode('utf-8'))
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        async with self._sem:
                            async with message.process():
                                try:
                                    task_payload = serializer(message.body)
                                except BaseException as e:
                                    logger.warning('parse json payload error: %s', e)
                                    task_payload = {}
                                asyncio.create_task(self.worker_init(task_payload))
                                if queue.name in message.body.decode():
                                    break
        except KeyboardInterrupt:
            logger.info('consumer shutdown')
            return

    async def worker_init(self, message):
        task = message.get('task', '')
        task_id = message.get('task_id')
        task_data = message.get('task_data', {})
        task_once_key = message.get('task_once_key', None)
        if task_once_key is not None:
            cache_key = method_cache_key(task=task, **task_data)
            if cache.get(cache_key) != task_once_key:
                logger.info('pass task %s by once condition (%s)', task,
                            ', '.join(['%s=%s' % item for item in task_data.items()]))
                return
        with ProcessPoolExecutor(max_workers=1) as executor:
            task = await self.loop.run_in_executor(executor, Process, message)
            task_model = {
                'id': task_id,
                'status': 'ok',
                'name': task,
                'data': task_data,
                'result': None,
                'error': None
            }
            if '_exception' in task.result:
                logger.warning('task %s got exception: %s' % (task, task.result['_exception']))
                task_model['status'] = 'error'
                task_model['error'] = {
                    'message': task.result.get('_exception'),
                    'traceback': task.result.get('_traceback', [])
                }
            else:
                task_model['result'] = task.result

            cache_key = method_cache_key(cache_prefix='task', task_id=task_id)
            cache.set(cache_key, task_model, 3600)

            if task_once_key is not None:
                cache_key = method_cache_key(task=task, **task_data)
                cache.delete(cache_key)

    # def callback(self, ch, method, properties, body):
    #     """
    #     Обработка аснихронной задачи в отдельном потоке для решения проблемы с долгоживущими задачами
    #
    #     https://github.com/pika/pika/issues/930#issuecomment-360333837
    #
    #     @param ch:
    #     @param method:
    #     @param properties:
    #     @param body:
    #     @return:
    #     """
    #
    #     # Парсим тело задачи и извлекаем от туда task и task_data. Task содержит пакет который будет запущен в
    #     # потоке, tas_data, необязательно содердит параметры к задаче
    #     try:
    #         task_payload = json.loads(body)
    #     except BaseException as e:
    #         logger.warning('parse json payload error: %s', e)
    #         task_payload = {}
    #
    #     task = task_payload.get('task', '')
    #     task_id = task_payload.get('task_id')
    #     task_headers = properties.headers
    #     task_data = task_payload.get('task_data', {})
    #
    #     # Проврка пропуска задачи. Если в кеше есть ключ '{TASK_CLASS}_{JSON_OF_BODY}' и его значение равно task_once_key то задачу
    #     # пропускаем, т.к. есть другая задача которая выполнится позже
    #     task_once_key = task_payload.get('task_once_key', None)
    #     if task_once_key is not None:
    #         cache_key = method_cache_key(task=task, **task_data)
    #         if cache.get(cache_key) != task_once_key:
    #             logger.info('pass task %s by once condition (%s)', task,
    #                         ', '.join(['%s=%s' % item for item in task_data.items()]))
    #             ch.basic_ack(delivery_tag=method.delivery_tag)
    #             return
    #
    #     if task:
    #         logger.info('process task %s (%s)', task, ', '.join(['%s=%s' % item for item in task_data.items()]))
    #
    #         try:
    #             result_queue = Queue()
    #             thread = threading.Thread(
    #                 target=lambda res_q, proxy, *args, **kwargs: res_q.put(proxy(*args, **kwargs)),
    #                 args=(
    #                     result_queue,
    #                     self.call_task_method,
    #                     task,
    #                     task_payload,
    #                     task_headers,
    #                     task_data,
    #                 ))
    #
    #             thread.start()
    #             while thread.is_alive():
    #                 self.bus_connection.sleep(1)
    #             thread.join()
    #
    #             task_result = result_queue.get()
    #             task_model = {
    #                 'id': task_id,
    #                 'status': 'ok',
    #                 'name': task,
    #                 'data': task_data,
    #                 'result': None,
    #                 'error': None
    #             }
    #             if '_exception' in task_result:
    #                 logger.warning('task %s got exception: %s' % (task, task_result['_exception']))
    #                 task_model['status'] = 'error'
    #                 task_model['error'] = {
    #                     'message': task_result.get('_exception'),
    #                     'traceback': task_result.get('_traceback', [])
    #                 }
    #             else:
    #                 task_model['result'] = task_result
    #
    #             cache_key = method_cache_key(cache_prefix='task', task_id=task_id)
    #             cache.set(cache_key, task_model, 3600)
    #         except BaseException as e:
    #
    #             # Ошибка внутри pika/amqp выводим exception в лог
    #             logger.exception(e)
    #
    #     else:
    #         logger.warning('not allowed task %s', task)
    #         # TODO: Изменить статус обработки на ошибку
    #
    #     if task_once_key is not None:
    #         cache_key = method_cache_key(task=task, **task_data)
    #         cache.delete(cache_key)
    #
    #     # в любом случае – текщую задачу ack`аем
    #     ch.basic_ack(delivery_tag=method.delivery_tag)
    #
    # def call_task_method(self, task_class, task_payload, task_headers, task_data, *args, **kwargs):
    #     try:
    #
    #         # Восстанавливаем задачу и запускаем обработку
    #         task: AsyncTask = self.import_task(task_class)(
    #             **{'task_headers': task_headers, **task_payload, **task_data})
    #         task_result = task.process()
    #
    #         # если задача отдала False – пытаемся повторить
    #         if not task_result:
    #
    #             # Если это нет логики повторов, то считаем что произошла ошибка
    #             if task.task_retry_logic is None:
    #
    #                 return {'_exception': 'Неизвестная ошибка', '_traceback': []}
    #
    #             # Иначе если есть логика повторов, делаем повтор задачи в соответствии с ней и если повторы закончились,
    #             # финализируем задачу и вовзращаем ошибку
    #             elif not task.publish(retry=True):
    #
    #                 # достигнут лимит повторений – финазилируем задачу
    #                 task.finalize()
    #                 return {'_exception': 'Достигнут лимит повторений задачи', '_traceback': []}
    #
    #         # Все хорошо, возвращаем результат из задачи
    #         else:
    #             return task_result
    #
    #     # Исключение вернули как ошибку и залогировали
    #     except Exception as e:
    #         logger.exception(e)
    #         return {'_exception': e.__str__(), '_traceback': traceback.format_exc()}
