from os import environ
from typing import Callable
import aio_pika

from app.messages.async_broker import AsyncBroker


class AsyncListener(AsyncBroker):
    def __init__(self, queue_name, processor: Callable[[str], None]):
        self.queue_name = queue_name
        self.message_processor = processor

    async def callback(self, message: aio_pika.abc.AbstractIncomingMessage):
        async with message.process():
            self.message_processor(message.body.decode())

    async def iterate_queue(self, queue: aio_pika.abc.AbstractQueue):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    self.message_processor(message.body.decode())

    async def listen(self, loop):
        connection = await self.default_connect_robust(loop)
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            environ.get("DEFAULT_EXCHANGE", "openferp"),
            type=aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        queue = await channel.declare_queue("rhevents/rh", durable=True)
        await queue.bind(exchange, routing_key=self.queue_name)
        await self.iterate_queue(queue)

        return connection
