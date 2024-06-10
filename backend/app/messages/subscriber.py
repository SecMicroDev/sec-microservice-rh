from os import environ
from typing import Callable
import aio_pika


class AsyncListener:
    def __init__(self, queue_name, processor: Callable[[str], None]):
        self.queue_name = queue_name
        self.message_processor = processor

    async def callback(self, message: aio_pika.abc.AbstractIncomingMessage):
        async with message.process():
            self.message_processor(message.body.decode())

    async def listen(self, loop):
        connection = await aio_pika.connect_robust(
            host=environ.get("BROKER_HOST", "my-rabbit"),
            username=environ.get("BROKER_USER", "guest"),
            password=environ.get("BROKER_PASS", "guest"),
            port=int(environ.get("BROKER_PORT", "5672")),
            loop=loop,
        )
        channel = await connection.channel()

        queue = await channel.declare_queue(self.queue_name, durable=True)
        await queue.consume(self.callback)

        # print(" [*] Waiting for messages. To exit press CTRL+C")
        # await asyncio.Future()  # Run forever
        return connection

    # def run_listener_thread(self):
    #     asyncio.run(self.listen())


# Example usage:
# if __name__ == "__main__":
#     listener = AioPikaListener(queue_name='async_queue')
#     asyncio.run(listener.listen())
