import asyncio
import json
import importlib
from multiprocessing import Process
# from aiokafka import AIOKafkaConsumer
from app.common.logger.logg import logger
from concurrent.futures import ProcessPoolExecutor


class Process:
    def __init__(self, message):
        self.message = message
        self.start()

    def start(self):
        task = getattr(importlib.import_module(self.message.get('module')), self.message.get('class_name'))
        instance = task(**self.message.get('parameters'))
        instance.process()


class CreateProcess:
    def __init__(self, max_workers):
        self.concurrent_workers = 0
        self.max_workers = max_workers
        self._sem = asyncio.Semaphore(self.max_workers)

    def run(self):
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.start_consume())
        self.loop.run_forever()

    async def start_consume(self):
        await asyncio.sleep(60)
        consumer = AIOKafkaConsumer(
            "import_task",
            bootstrap_servers=f'{setting.KAFKA_HOST}:{setting.KAFKA_PORT}',
            group_id="import",
            value_deserializer=lambda x: json.loads(x.decode('utf-8')))
        logger.info("Starting consumer")
        await consumer.start()
        async for msg in consumer:
            # print("consumed: ", msg.topic, msg.partition, msg.offset,
            #       msg.key, msg.value, msg.timestamp)
            logger.info(msg.value)
            asyncio.create_task(self.worker_init(msg.value))
            await asyncio.sleep(0)

    async def worker_init(self, message):
        async with self._sem:
            with ProcessPoolExecutor(max_workers=1) as executor:
                extract_data = await self.loop.run_in_executor(executor, Process, message)


if __name__ == "__main__":
    processing = CreateProcess(max_workers=4)
    processing.run()
