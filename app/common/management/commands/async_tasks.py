import importlib
import json
import logging
import threading
import traceback
from queue import Queue

from django.core.cache import cache
from app.common.logger.logg import logger
from app.common.utils import method_cache_key
from django.core.management import BaseCommand
from app.common.async_task_interface.bus import Bus
from app.common.async_task_interface.tasks import Resolver, AsyncTask


class Command(Bus, BaseCommand):
    """
    Асинхронные методы, не возвращающие данные непосредственно пользователям.
    """

    help = 'Process async tasks'

    async_tasks = []

    def handle(self, *args, **kwargs):
        logger.info('load asynchronous task')

        self.async_tasks = Resolver().resolve_apps()

        logger.info('loaded tasks %s', json.dumps(self.async_tasks, indent='  '))
        logger.info('asynchronous task started')

        while True:
            self.bus_channel.basic_qos(prefetch_count=1)
            self.bus_channel.basic_consume(queue=self.QUEUE_TPL['TASKS'].format(ns=self.bus_ns),
                                           on_message_callback=self.callback)
            try:
                self.bus_channel.start_consuming()
            except KeyboardInterrupt:
                self.bus_channel.stop_consuming()
                logger.info('consumer shutdown')
                return

            logger.warning('consumer was interrupted, try again ...')

    def callback(self, ch, method, properties, body):
        """
        Обработка аснихронной задачи в отдельном потоке для решения проблемы с долгоживущими задачами

        https://github.com/pika/pika/issues/930#issuecomment-360333837

        @param ch:
        @param method:
        @param properties:
        @param body:
        @return:
        """

        # Парсим тело задачи и извлекаем от туда task и task_data. Task содержит пакет который будет запущен в
        # потоке, tas_data, необязательно содердит параметры к задаче
        try:
            task_payload = json.loads(body)
        except BaseException as e:
            logger.warning('parse json payload error: %s', e)
            task_payload = {}

        task = task_payload.get('task', '')
        task_id = task_payload.get('task_id')
        task_headers = properties.headers
        task_data = task_payload.get('task_data', {})

        # Проврка пропуска задачи. Если в кеше есть ключ '{TASK_CLASS}_{JSON_OF_BODY}' и его значение равно task_once_key то задачу
        # пропускаем, т.к. есть другая задача которая выполнится позже
        task_once_key = task_payload.get('task_once_key', None)
        if task_once_key is not None:
            cache_key = method_cache_key(task=task, **task_data)
            if cache.get(cache_key) != task_once_key:
                logger.info('pass task %s by once condition (%s)', task,
                            ', '.join(['%s=%s' % item for item in task_data.items()]))
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

        if task in self.async_tasks:
            logger.info('process task %s (%s)', task, ', '.join(['%s=%s' % item for item in task_data.items()]))

            try:
                result_queue = Queue()
                thread = threading.Thread(
                    target=lambda res_q, proxy, *args, **kwargs: res_q.put(proxy(*args, **kwargs)),
                    args=(
                        result_queue,
                        self.call_task_method,
                        task,
                        task_payload,
                        task_headers,
                        task_data,
                    ))

                thread.start()
                while thread.is_alive():
                    self.bus_connection.sleep(1)
                thread.join()

                task_result = result_queue.get()
                task_model = {
                    'id': task_id,
                    'status': 'ok',
                    'name': task,
                    'data': task_data,
                    'result': None,
                    'error': None
                }
                if '_exception' in task_result:
                    logger.warning('task %s got exception: %s' % (task, task_result['_exception']))
                    task_model['status'] = 'error'
                    task_model['error'] = {
                        'message': task_result.get('_exception'),
                        'traceback': task_result.get('_traceback', [])
                    }
                else:
                    task_model['result'] = task_result

                cache_key = method_cache_key(cache_prefix='task', task_id=task_id)
                cache.set(cache_key, task_model, 3600)
            except BaseException as e:

                # Ошибка внутри pika/amqp выводим exception в лог
                logger.exception(e)

        else:
            logger.warning('not allowed task %s', task)
            # TODO: Изменить статус обработки на ошибку

        if task_once_key is not None:
            cache_key = method_cache_key(task=task, **task_data)
            cache.delete(cache_key)

        # в любом случае – текщую задачу ack`аем
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def call_task_method(self, task_class, task_payload, task_headers, task_data, *args, **kwargs):
        try:

            # Восстанавливаем задачу и запускаем обработку
            task: AsyncTask = self.import_task(task_class)(
                **{'task_headers': task_headers, **task_payload, **task_data})
            task_result = task.process()

            # если задача отдала False – пытаемся повторить
            if not task_result:

                # Если это нет логики повторов, то считаем что произошла ошибка
                if task.task_retry_logic is None:

                    return {'_exception': 'Неизвестная ошибка', '_traceback': []}

                # Иначе если есть логика повторов, делаем повтор задачи в соответствии с ней и если повторы закончились,
                # финализируем задачу и вовзращаем ошибку
                elif not task.publish(retry=True):

                    # достигнут лимит повторений – финазилируем задачу
                    task.finalize()
                    return {'_exception': 'Достигнут лимит повторений задачи', '_traceback': []}

            # Все хорошо, возвращаем результат из задачи
            else:
                return task_result

        # Исключение вернули как ошибку и залогировали
        except Exception as e:
            logger.exception(e)
            return {'_exception': e.__str__(), '_traceback': traceback.format_exc()}

    @staticmethod
    def import_task(task_name):
        logger.debug('import task %s', task_name)
        pkg, attr = task_name.rsplit('.', 1)
        logger.debug('pkg %s, module %s', pkg, attr)
        ret = getattr(importlib.import_module(pkg), attr)
        return ret
