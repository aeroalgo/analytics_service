import os
import sys
import time
import json
import signal
import asyncio
import aiohttp
import orjson
import requests
import traceback
from functools import partial
from abc import abstractmethod
from aiohttp import ClientTimeout
from typing import Optional, Callable
from concurrent.futures import ProcessPoolExecutor

from app.common.async_task_interface.tasks import AsyncTask
from app.common.logger.logg import logger


class Task:
    """
    Класс задачи запроса данных

    """
    content_path = ''
    status = ''

    def __init__(self, url: str, count_call=0, tid: Optional[int] = None, callback: Optional[Callable] = None,
                 cd_kwargs: dict = None, content=False, save_content: bool = False,
                 start_extract: Optional[Callable] = None, executor: Optional[ProcessPoolExecutor] = None,
                 called_class=None, model=None, headers=None, payload=None, cookies=None, auto_decompress=True,
                 string_data=None):
        self.count_call = count_call
        self.cookies = cookies
        self.payload = payload
        self.headers = headers
        self.model = model
        self.tid = tid
        self.url = url
        self.executor = executor
        self.start_extract = start_extract
        self.callback = callback
        self.called_class = called_class
        self.cd_kwargs = cd_kwargs
        self.content = content
        self.save_content = save_content
        self.auto_decompress = auto_decompress
        self.string_data = string_data

    async def perform(self):
        extract_data = None
        status = None
        try:
            timeout = ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout, headers=self.headers) as session:
                if self.payload:
                    resp = await session.post(url=self.url, json=self.payload)
                elif self.string_data:
                    resp = await session.post(url=self.url, data=self.string_data)
                else:
                    resp = await session.get(url=self.url)
                self.status = resp.status
                if self.status == 200:
                    if self.cookies is None:
                        self.cookies = resp.cookies
                    loop = asyncio.get_running_loop()
                    with ProcessPoolExecutor(max_workers=1) as executor:
                        if not self.content:
                            data = await resp.text()
                            try:
                                if self.callback is None:
                                    extract_data = await loop.run_in_executor(
                                        executor, partial(self.start_extract, orjson.loads(data), self.headers,
                                                          self.cookies))
                                else:
                                    extract_data = await loop.run_in_executor(
                                        executor, partial(self.callback, orjson.loads(data), self.headers,
                                                          self.cookies, self.payload or self.string_data,
                                                          self.cd_kwargs))
                            except KeyboardInterrupt:
                                logger.info("All process close")
                        else:
                            extract_data = await loop.run_in_executor(executor,
                                                                      partial(None, self.callback, self.url))
                    if extract_data is not None:
                        for data in extract_data:
                            try:
                                if isinstance(data, Task):
                                    await self.called_class.put(data)
                                else:
                                    await data.save_or_update()
                            except Exception as e:
                                logger.error(msg=e, exc_info=True)
                                continue
                else:
                    if self.count_call <= 2:
                        self.count_call += 1
                        logger.info(self.payload)
                        logger.info(self.headers)
                        await self.called_class.put(self)
                        await session.close()
        except Exception as e:
            logger.error(msg=self.headers, exc_info=True)
            self.status = f'skipped, {status}'
            if self.count_call <= 3:
                self.count_call += 1
                logger.info(self.payload)
                await self.called_class.put(self)


class ExtractData:
    """
    Интерфейс класса парсинга

    """
    content_path = ''

    def download_content(self, url):
        full_content_path = self.content_path + url.split("/")[-1]
        with open(full_content_path, "wb") as f:
            f.write(requests.get(url).content)
            print('download successful: ', full_content_path)

    @classmethod
    @abstractmethod
    def start_extract(cls, response, headers, cookie):
        """Начальный метод извлечения данных"""


class Pool(AsyncTask):
    def __init__(self, max_rate: int, param, extract_data_class: ExtractData,
                 interval: float = 1, concurrent_level: Optional[int] = None):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        except RuntimeError as e:
            if str(e).startswith('There is no current event loop in thread'):
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            else:
                self._loop = asyncio.get_event_loop()
        self.start_extract = extract_data_class.start_extract
        self.start_url: list = []
        self.max_rate: int = max_rate
        self.interval: float = interval
        self._between_requests = interval / self.max_rate
        self.concurrent_level: int = concurrent_level
        self.is_running: bool = False
        self._queue = asyncio.Queue()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._sem = asyncio.Semaphore(concurrent_level or self.max_rate)
        self._stop_event = asyncio.Event()
        self._add_task_queue = asyncio.Event()
        self._concurrent_workers = 0
        self.start_time = time.time()
        self.count = 0
        self.up_rate = self.max_rate * 10
        self.old_rate = self.max_rate
        super().__init__(param=param)

    def handler(self, signum, frame):
        print('SIGINT for PID=', os.getpid())
        sys.exit(0)

    def initializer(self):
        signal.signal(signal.SIGINT, self.handler)

    async def _scheduler(self):
        count = 1
        while self.is_running:
            for _ in range(self.max_rate):
                # print('Queue size', self._queue.qsize())
                if self._queue.qsize() != 0:
                    async with self._sem:
                        task = await self._queue.get()
                        task.tid = count
                        asyncio.create_task(self._worker(task))
                        self._add_task_queue.set()
                        await asyncio.sleep(self._between_requests)
                        count += 1
                    await asyncio.sleep(0)
                else:
                    # print('Active tasks count:',
                    #       len([task for task in asyncio.all_tasks(self._loop) if not task.done()]))
                    await asyncio.sleep(0.1)

    async def _worker(self, task: Task):
        async with self._sem:
            self._concurrent_workers += 1
            task.called_class = self
            await task.perform()
        self._queue.task_done()
        await asyncio.sleep(0)
        self.count += 1
        if task.tid % 20 == 0:
            logger.info(
                msg=f'tid = {task.tid} all_count = {self.count} {task.url} {task.status} '
                    f'{round((time.time() - self.start_time), 3)} seconds')
        if task.status == 'skipped' and self.max_rate != self.up_rate:
            self.change_rate_skipped(self.up_rate)
        elif task.status == 200 and self.max_rate != self.old_rate:
            self.change_rate_skipped(self.old_rate)
        self._concurrent_workers -= 1
        if not self.is_running and self._concurrent_workers == 0:
            self._stop_event.set()

    def change_rate_skipped(self, rate):
        self.max_rate = rate
        self._sem = asyncio.Semaphore(self.max_rate)
        self._between_requests = self.interval / self.max_rate

    async def stop(self):
        self.is_running = False
        self._scheduler_task.cancel()
        if self._concurrent_workers != 0:
            await self._stop_event.wait()
        logger.info(f'Stoping {self.__class__.__name__}')

    def start(self):
        self.is_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler())

    async def put(self, task: Task):
        await self._queue.put(task)

    async def first_tasks(self):
        if self.start_url:
            for url in self.start_url:
                await self.put(
                    Task(url=url.get('url'), start_extract=self.start_extract,
                         headers=url.get('headers'), payload=url.get('payload')))
                if not self.is_running:
                    self.start()
                if self._queue.qsize() >= self.max_rate:
                    await self._queue.join()
                await self._add_task_queue.wait()
                self._add_task_queue.clear()
            for i in range(60):
                await self._queue.join()
                await asyncio.sleep(1)
            await self.stop()

    def create_first_tasks(self):
        try:
            logger.info(f'Starting {self.__class__.__name__}')
            self._loop.run_until_complete(self.first_tasks())
        except KeyboardInterrupt:
            self._loop.run_until_complete(self.stop())
            self._loop.close()
