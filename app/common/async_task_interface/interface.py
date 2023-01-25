import os
import sys
import uuid
from abc import abstractmethod


class ProcessAsyncTask:
    """Класс отвечающий за первоначальную настройку пула задач"""

    def __init__(self, **kwargs):
        self.task_id = str(kwargs.get('task_id', uuid.uuid4()))
        self.import_message = {
            'module': self.__class__.__module__,
            'class_name': self.__class__.__name__,
            'parameters': {**kwargs}
        }


    @abstractmethod
    async def publish(self):
        """ Оповещение о начале и отправка в очередь """

    @abstractmethod
    def process(self):
        """ Выполнение асинхронной задачи """

    @abstractmethod
    async def finalize(self):
        """ Оповещение об окончании """
