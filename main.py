from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from faststream import FastStream

import routes
from common.database.session import dispose_database
from common.enums.consumer import ConsumerName
from common.services.broker_client import BrokerClient
from config import settings
from routes.handler import payment_handler_router
from services.outbox import OutboxPublisher

api_broker_client = BrokerClient(app_id=settings.service_name)
consumer_broker_client = BrokerClient(
    app_id=ConsumerName.PAYMENT_PROCESSOR,
    prefetch_count=1,
)
consumer_broker_client.broker.include_router(payment_handler_router)
consumer_app = FastStream(consumer_broker_client.broker)


@consumer_app.after_startup
async def setup_consumer_topology() -> None:
    await consumer_broker_client.initialize_queues()


@consumer_app.after_shutdown
async def dispose_consumer_database() -> None:
    await dispose_database()


def run_consumer() -> None:
    import asyncio

    asyncio.run(consumer_app.run())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await api_broker_client.start()

    outbox_publisher = OutboxPublisher(api_broker_client.broker)
    await outbox_publisher.start()

    app.state.broker = api_broker_client.broker
    app.state.outbox_publisher = outbox_publisher

    try:
        yield
    finally:
        await outbox_publisher.stop()
        await api_broker_client.stop()
        await dispose_database()


app = FastAPI(lifespan=lifespan)

for router in routes.__all__:
    app.include_router(router)
