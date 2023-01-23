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
    def run(self):
        """Запуск publish asyncio.run()"""

    @abstractmethod
    async def publish(self):
        """Оповещение о начале парсинга и импорт в процессорный пул задач"""

    @abstractmethod
    def process(self):
        """ Настройка headers и первоначальных куки """

    @abstractmethod
    async def finalize(self):
        """Оповещение об окончании парсинга"""
