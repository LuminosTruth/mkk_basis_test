from faststream.rabbit import Channel, ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from common.enums.queue import QueueName
from common.enums.subject import SubjectType
from config import settings

PAYMENTS_EXCHANGE_NAME = "payments.exchange"
PAYMENTS_DLX_NAME = "payments.dlx"
PAYMENTS_DLQ_ROUTING_KEY = "payments.failed"

PAYMENTS_EXCHANGE = RabbitExchange(
    PAYMENTS_EXCHANGE_NAME,
    type=ExchangeType.TOPIC,
    durable=True,
)
PAYMENTS_DLX = RabbitExchange(
    PAYMENTS_DLX_NAME,
    type=ExchangeType.DIRECT,
    durable=True,
)
PAYMENTS_QUEUE = RabbitQueue(
    QueueName.PAYMENTS_NEW,
    durable=True,
    routing_key=SubjectType.PAYMENT_CREATED,
    arguments={
        "x-dead-letter-exchange": PAYMENTS_DLX_NAME,
        "x-dead-letter-routing-key": PAYMENTS_DLQ_ROUTING_KEY,
    },
)
PAYMENTS_RETRY_QUEUE = RabbitQueue(
    QueueName.PAYMENTS_RETRY,
    durable=True,
    arguments={
        "x-dead-letter-exchange": PAYMENTS_EXCHANGE_NAME,
        "x-dead-letter-routing-key": SubjectType.PAYMENT_CREATED,
    },
)
PAYMENTS_DLQ = RabbitQueue(
    QueueName.PAYMENTS_DLQ,
    durable=True,
    routing_key=PAYMENTS_DLQ_ROUTING_KEY,
)


class BrokerClient:
    def __init__(self, app_id: str, prefetch_count: int | None = None) -> None:
        broker_kwargs = {"app_id": app_id}
        if prefetch_count is not None:
            broker_kwargs["default_channel"] = Channel(prefetch_count=prefetch_count)

        self.broker = RabbitBroker(settings.rabbitmq_url, **broker_kwargs)

    async def start(self) -> None:
        await self.broker.start()
        await self.initialize_queues()

    async def stop(self) -> None:
        await self.broker.stop()

    async def initialize_queues(self) -> None:
        payments_exchange = await self.broker.declare_exchange(PAYMENTS_EXCHANGE)
        dlx = await self.broker.declare_exchange(PAYMENTS_DLX)

        payments_queue = await self.broker.declare_queue(PAYMENTS_QUEUE)
        await payments_queue.bind(
            payments_exchange,
            routing_key=SubjectType.PAYMENT_CREATED,
        )

        await self.broker.declare_queue(PAYMENTS_RETRY_QUEUE)

        dlq = await self.broker.declare_queue(PAYMENTS_DLQ)
        await dlq.bind(dlx, routing_key=PAYMENTS_DLQ_ROUTING_KEY)
