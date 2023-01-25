import inspect
import json
import logging
import uuid
from abc import abstractmethod
from django.apps import apps
from django.core.cache import cache
from app.common.logger.logg import logger

from app.common.async_task_interface.bus import Bus
from app.common.utils import method_cache_key


class AsyncTask(Bus):
    """
    Базовый класс для асинхронной задачи.

    Что-бы создать асинхронную задачу нужно
    - определить класс и наследоваться от AsyncTask
    - определить конструктор если нужно, вызвав в начале super.__init__(*args, **kwargs)
    - передать в конструкторе класса param super().__init__(param={
            "value": self.value,
        })
    - реализовать два обязательных метода process(), finalize()

    Класс AsyncTask имеет некоторые базовые свойства

    - task_class это свойство readonly задает имя класса (+питоний модуль) задачи которая наследует базовый
    - task_id авто-генерируемый uuid задачи
    - task_delay установив одно из значений Bus.DURATIONS можно отправить задачу на выполнение с
        задержкой в указанных секундах
    - task_retry_logic установка стратегии интервалов, с помощью этой опции мы указываем
        что задача retryable и имеет одну из стратегий интервалов указанных в Bus.RETRY_LOGIC_*
    - task_once делает задачу выполняемой единоразово, только последняя задача с task_class и @task_data будет
        выполнена, остальные более старые будут пропущены (ack)
    из этих свойств, вот эти task_delay, task_retry_logic, task_once передаются как аргументы при создании
        инстанса задачи перед ее публикацией

    """

    def __init__(self, *args, **kwargs):
        self.task_module = self.__class__.__module__
        self.task_class = self.__class__.__name__
        self.task_id = str(kwargs.get('task_id', uuid.uuid4()))
        self.task_delay = kwargs.get('task_delay', None)
        self.task_retry_logic = kwargs.get('task_retry_logic', None)
        self.task_once = bool(kwargs.get('task_once', False))
        self.task_headers = kwargs.get('task_headers', None)
        self.task_data = kwargs.get('param', None)

    def publish(self, retry=False, **kwargs):
        """
        Формирование аргументов и отправка сообщения в RabbitMQ

        @param retry:
        @return:
        """
        self.task_delay = kwargs.get('task_delay', self.task_delay)
        self.task_retry_logic = kwargs.get('task_retry_logic', self.task_retry_logic)
        self.task_once = kwargs.get('task_once', self.task_once)

        # По умолчанию отправляем как обычная задача
        publish_kwargs = {
            'exchange': self.EXCHANGE_TPL['TASKS'].format(ns=self.bus_ns),
            'routing_key': self.QUEUE_TPL['TASKS'].format(ns=self.bus_ns),
        }

        # Отправка с задержкой
        if self.task_delay in self.DURATIONS:
            publish_kwargs['exchange'] = ''
            publish_kwargs['routing_key'] = self.QUEUE_TPL['DELAY_TASKS'].format(ns=self.bus_ns,
                                                                                 duration=self.task_delay)

        # Отправка с логикой повторов, вначале самый первый duration из логики повторов
        retry_logic = dict(self.RETRY_LOGIC).get(self.task_retry_logic)
        if isinstance(retry_logic, dict):
            logger.debug(f'apply retry logic {self.task_retry_logic}')

            publish_kwargs['exchange'] = ''

            # Если это повтор задачи, извлекаем кол-во смертей и получаем следующее значение интервала,
            # если попытки иссякли, вернем False
            if retry:

                # Если нет headers, то не было повторяемой задачи
                if self.task_headers is None:
                    return False

                retires_count = sum([x.get('count') for x in self.task_headers.get('x-death', [])])
                publish_kwargs['routing_key'] = self._get_queue_name_by_retries_count(retires_count=retires_count,
                                                                                      retry_logic=self.task_retry_logic)

                # количество попыток иссякло – не добавляем в очередь
                if publish_kwargs['routing_key'] is None:
                    return False
            else:
                publish_kwargs['routing_key'] = self.QUEUE_TPL['RETRY_TASKS'].format(ns=self.bus_ns, duration=next(
                    iter(retry_logic.keys())))

        # Формируем тело сообщения, задачу пакуем следующим образом
        # - task это fullyqualified class name задачи
        # - task_id это уникальный идентификатор задачи
        body = {
            'task_class': self.task_class,
            'task_module': self.task_module,
            'task_id': self.task_id,
            'task_retry_logic': self.task_retry_logic,
            'task_once': self.task_once,
            'task_delay': self.task_delay,
            'task_data': self.task_data,
        }

        # Обозначаем задачу как выполняему только один раз
        if self.task_once:
            body['task_once_key'] = str(uuid.uuid4())
            logger.debug('once task with id %s' % body['task_once_key'])
            cache_key = method_cache_key(task=self.task_class, **body['task_data'])
            cache.set(cache_key, body['task_once_key'], 3600)

        # Все тело задачи пакуем в JSON байты, логгируем и отправляем
        publish_kwargs['body'] = str.encode(json.dumps(body))
        logger.info(f'publish task {self.task_class}, \n {publish_kwargs}')
        self.open_channel(publish_kwargs)

        return True

    @abstractmethod
    def process(self):
        """
        Обработка задачи.

        В случае исключения ошибка отлавливается вне задачи в коде async_tasks и задача помечается в redis с ошибкой и статусом error
        Если все ок, нужно вернуть что то не похожее на False, например {'status': 'ok'}

        @return:
        """
        pass

    @abstractmethod
    def finalize(self):
        """
        Финализация задачи.

        Используется если метод process вернул что то похожее на False и если это задача с логикой повторов (RETRY_LOGIC_*) то при истичении
        повторов.
        @return:
        """
        pass
