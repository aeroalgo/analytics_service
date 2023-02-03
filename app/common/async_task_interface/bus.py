import itertools
import json
import logging
import random
import sys
import uuid
import asyncio
import aio_pika
import pika
from django.conf import settings
from django.core.cache import cache
from pika import BlockingConnection
from app.common.logger.logg import logger


class Bus:
    """
    Шина для асинхроных задач.

    Обертка над RabbitMQ инкапсулюрующая логику распределения асинхронных задач, их повторов, задержек и т.д.

    - При создании экземпляра класса, будут доступны bus_connection, bus_channel соответственно соединение и канал с RabbitMQ для работы
    с ним.
    - Если соединение или канал не был подключен, будет произведено соединение
    - При соединении будут созданы exchanges

        - '{RABBIT.USER}' основная точка обмена, сюда отправляются задачи без интервалов
        - '{RABBIT.USER}__retryable' точка обмена для задач с логикой retryable (повторы)

        очереди:

        - '{RABBIT.USER}__tasks' очередь куда попадают все задачи и откуда ведется их обработка
        - '{RABBIT.USER}__retry__XXXXs' это очереди с установленым TTL для задач которые будут повторяться, после истечения TTL сообщение
           отправится в exchange '{RABBIT.USER}__retryable' с routing_key '{RABBIT.USER}__tasks' и если там задача выполнится с ошибкой
           будет снова создано сообщение в этой очереди, но с следующим интервалом
        - '{RABBIT.USER}__delay__XXXXs' это очереди с установленым TTL для отложеных во времени задачах, после истечения TTL сообщение
           отправится в exchange '{RABBIT.USER}' с routing_key '{RABBIT.USER}__tasks' п

    Для публикации задач в шину, нужно создать класс задачи отнаследоваться от AsyncTask класса и вызвать метод экземпляра publish()

    ```
    class MyTask(AsyncTask):
        def process(self):
            print('processing...')
            return {'status': 'ok'}
        def finalize(self):
            print('task finalize...')

    ...

    my_task = Task()
    my_task.publish()

    print(f'task {my_task.task_class} published success with id {my_task.task_id}')
    ```

    """
    _connection = None
    _channel = None

    EXCHANGE_TPL = {
        'TASKS': '{ns}',
        'RETRYABLE_TASKS': '{ns}__retryable',
    }

    QUEUE_TPL = {
        'TASKS': '{ns}__tasks',
        'RETRY_TASKS': '{ns}__retry__{duration:04}s',
        'DELAY_TASKS': '{ns}__delay__{duration:04}s',
    }

    """
    Логика повторов:

    - 2 раза по 5 секунд
    - 5 раз по 10 секунд
    - 200 раз по 10 минут

    общее время повторов – ~2 часа

    Количество секунд => количество повторов
    """
    RETRY_LOGIC_2DAYS_EVERY_10MINUTES = '2d_every_10m'

    """
    Логика повторов:

    - 2 раза по 5 секунд
    - 5 раз по 10 секунд
    - 20 раз по 60 секунд
    - 5 раз по 10 минут
    - 47 раз по 1 часу

    общее время повторов – ~2 часа

    Количество секунд => количество повторов
    """
    RETRY_LOGIC_2DAYS_EVERY_HOUR = '2d_every_1h'

    RETRY_LOGIC = (
        (RETRY_LOGIC_2DAYS_EVERY_10MINUTES, {
            5: 2,
            10: 5,
            600: 200,
        }),
        (RETRY_LOGIC_2DAYS_EVERY_HOUR, {
            5: 2,
            10: 5,
            60: 20,
            600: 5,
            3600: 47
        }),
    )

    DURATIONS = set(list(itertools.chain.from_iterable([logic.keys() for _, logic in RETRY_LOGIC])))

    def _get_queue_name_by_retries_count(self, retires_count, retry_logic):
        """
        Возвращает название очереди по количеству совершенных попыток повторов.
        Если больше нет повторов – возвращает None
        """
        intervals_limits = list(itertools.accumulate(retry_logic.values()))
        interval_value = None
        found_interval_count = next(filter(lambda x, y=retires_count: y <= x, intervals_limits), None)
        if found_interval_count is not None:
            interval_value = list(retry_logic.keys())[intervals_limits.index(found_interval_count)]

        if interval_value is None:
            return None

        return self.QUEUE_TPL['RETRY_TASKS'].format(ns=self.bus_ns, duration=interval_value)

    def open_channel(self, msg):
        asyncio.run(self._connect(msg))

    @property
    def bus_ns(self):
        return settings.RABBITMQ['USER']

    async def _connect(self, msg):
        """
        Установка соединения с RabbitMQ и инициализация exchanges, queues

        @return:
        """
        connection = await aio_pika.connect(url=settings.RABBITMQ_URL)
        async with connection:
            # Creating channel
            channel = await connection.channel()
            exchange = await self._declare(channel=channel, msg=msg)
            await exchange.publish(aio_pika.Message(msg.get('body')), routing_key=msg.get('routing_key'))

    async def _declare(self, channel, msg):
        # Объявление точек обмена (exchanges)
        exchange_tasks = self.EXCHANGE_TPL['TASKS'].format(ns=self.bus_ns)
        exchange_retryable_tasks = self.EXCHANGE_TPL['RETRYABLE_TASKS'].format(ns=self.bus_ns)
        exchanges = {
            exchange_tasks: await channel.declare_exchange(name=exchange_tasks, durable=True, auto_delete=False),
            exchange_retryable_tasks: await channel.declare_exchange(name=exchange_retryable_tasks, durable=True,
                                                                     auto_delete=False)
        }
        # Объявление очереди для обработки задач
        queue_tasks = self.QUEUE_TPL['TASKS'].format(ns=self.bus_ns)

        queue = await channel.declare_queue(name=queue_tasks, durable=True)
        await queue.bind(exchanges.get(exchange_tasks))
        await queue.bind(exchanges.get(exchange_retryable_tasks))

        # Объявления очередей для работы с задежками, повторами
        for duration in self.DURATIONS:
            await channel.declare_queue(
                name=self.QUEUE_TPL['DELAY_TASKS'].format(ns=self.bus_ns, duration=duration),
                durable=True,
                arguments={
                    'x-message-ttl': duration * 1000,
                    'x-dead-letter-exchange': exchange_tasks,
                    'x-dead-letter-routing-key': queue_tasks,
                },
            )

            await channel.declare_queue(
                name=self.QUEUE_TPL['RETRY_TASKS'].format(ns=self.bus_ns, duration=duration),
                durable=True,
                arguments={
                    'x-message-ttl': duration * 1000,
                    'x-dead-letter-exchange': exchange_retryable_tasks,
                    'x-dead-letter-routing-key': queue_tasks,
                },
            )

        return exchanges.get(msg.get("exchange"))