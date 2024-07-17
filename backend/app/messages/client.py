from asyncio import AbstractEventLoop
from datetime import datetime as dt, timedelta, timezone
import json
from json.decoder import JSONDecodeError
from os import environ
from typing import Any

from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractMessage
import pika

from app.messages.async_broker import AsyncBroker


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


class AsyncSender(AsyncBroker):
    def __init__(self, queue_name):
        self.queue_name = queue_name

    def default_exchange(self, channel: AbstractChannel):
        return channel.declare_exchange(
            environ.get("DEFAULT_EXCHANGE", "openferp"),
            durable=bool(environ.get("EXCHANGE_DURABLE", "True")),
            type=ExchangeType.TOPIC,
        )

    async def publish_to(
        self, route: str, exchange: AbstractExchange, message: AbstractMessage
    ):
        await exchange.publish(routing_key=f"rh_event.{route}", message=message)
        print(f"Published on Exchange {exchange.name}, {str(exchange)}")

    async def publish(self, message_body: str, loop: AbstractEventLoop):
        print("Connecting to broker...")
        connection = await self.default_connect_robust(loop)

        print("Returning channel...")

        channel = await connection.channel()
        body: dict[str, Any] = {}

        try:

            body = json.loads(message_body)
            body.update({"origin": "rh"})
            body.update(
                {
                    "start_date": dt.now(
                        tz=timezone(timedelta(0), name="UTC")
                    ).isoformat()
                }
            )

            message_body = json.dumps(body)

        except (JSONDecodeError, KeyError):
            print("Invalid JSON message")
            return connection

        message = Message(
            message_body.encode("ascii"),
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        exchange = await self.default_exchange(channel)
        print("publishing to queue")

        for route in ["sells", "pt"]:
            await self.publish_to(route, exchange, message)

        return connection
