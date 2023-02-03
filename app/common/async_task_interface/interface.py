import os
import sys
import uuid
from abc import abstractmethod


class ProcessAsyncTask:
    """Класс отвечающий за первоначальную настройку пула задач"""

    def __init__(self, **kwargs):
        self.task_id = str(kwargs.get('task_id', uuid.uuid4()))
        self.task_delay = kwargs.get('task_delay', None)
        self.task_retry_logic = kwargs.get('task_retry_logic', None)
        self.task_once = bool(kwargs.get('task_once', False))


    @abstractmethod
    async def publish(self):
        """ Оповещение о начале и отправка в очередь """

    @abstractmethod
    def process(self):
        """ Выполнение асинхронной задачи """

    @abstractmethod
    async def finalize(self):
        """ Оповещение об окончании """
