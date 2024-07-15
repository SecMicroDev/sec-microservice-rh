from asyncio import AbstractEventLoop
from datetime import datetime as dt, timedelta, timezone
from json.decoder import JSONDecodeError
from os import environ
from typing import Any
import aio_pika
from aio_pika import ExchangeType, Message, DeliveryMode
import pika
import json


class SyncSender:
    def __init__(self, queue_name):
        self.queue_name = queue_name
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=environ.get("BROKER_HOST", "my-rabbit"),
                port=int(environ.get("BROKER_PORT", "5672")),
                credentials=pika.PlainCredentials(
                    username=environ.get("BROKER_USER", "guest"),
                    password=environ.get("BROKER_PASS", "guest"),
                ),
            )
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue_name, durable=True)

    def send_message(self, message):
        self.channel.basic_publish(
            exchange="", routing_key=self.queue_name, body=message
        )
        print(f" [x] Sent '{message}'")

    def close_connection(self):
        self.connection.close()


class AsyncSender:
    def __init__(self, queue_name):
        self.queue_name = queue_name

    async def publish(self, message_body: str, loop: AbstractEventLoop):
        print("Connecting to broker...")
        connection = await aio_pika.connect_robust(
            host=environ.get("BROKER_HOST", "my-rabbit"),
            username=environ.get("BROKER_USER", "guest"),
            password=environ.get("BROKER_PASS", "guest"),
            port=int(environ.get("BROKER_PORT", "5672")),
            loop=loop,
        )

        print("Returning channel...")

        channel = await connection.channel()
        body: dict[str, Any] = {}

        try:
            body = json.loads(message_body)
            body.update(dict(origin="rh"))
            body.update(
                dict(
                    start_date=dt.now(tz=timezone(timedelta(0), name="UTC")).isoformat()
                )
            )
            message_body = json.dumps(body)
        except JSONDecodeError | KeyError:
            print("Invalid JSON message")
            return connection

        message = Message(
            message_body.encode("ascii"),
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        exchange = await channel.declare_exchange(
            environ.get("DEFAULT_EXCHANGE", "openferp"),
            durable=bool(environ.get("EXCHANGE_DURABLE", "True")),
            type=ExchangeType.TOPIC,
        )

        print("publishing to queue")

        async def publish_to(route: str):
            await exchange.publish(routing_key=f"rh_event.{route}", message=message)
            print(f"Published on Exchange {exchange.name}, {exchange.__str__()}")

        for route in ["sells", "pt"]:
            await publish_to(route)

        # print(" [*] Waiting for messages. To exit press CTRL+C")
        # await asyncio.Future()  # Run forever
        return connection


# def main():
#     sender = PikaSender(queue_name='rh_event_queue')
#     try:
#         while True:
#             message = input("Enter the message to send: ")
#             threading.Thread(target=run_sender, args=(sender, message)).start()
#     except KeyboardInterrupt:
#         print("Exiting...")
#     finally:
#         sender.close_connection()

# if __name__ == "__main__":
#     main()
