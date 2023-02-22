import asyncio
import importlib
import json
import logging
import threading
import time
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
        self.result = {}
        self.start()

    def start(self):
        try:
            task = getattr(importlib.import_module(self.message.get('task_module')), self.message.get('task_class'))
            instance = task(**self.message.get('task_data'))
            self.result = instance.process()

            if not self.result:

                # Если нет логики повторов, то считаем что произошла ошибка
                if instance.task_retry_logic is None:

                    self.result = {'_exception': 'Неизвестная ошибка', '_traceback': []}

                # Иначе если есть логика повторов, делаем повтор задачи в соответствии с ней и если повторы закончились,
                # финализируем задачу и возвращаем ошибку
                elif not instance.publish(retry=True):

                    # достигнут лимит повторений – финазилируем задачу
                    instance.finalize()
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
        time.sleep(20)
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
