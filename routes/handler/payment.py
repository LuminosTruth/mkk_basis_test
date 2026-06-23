import logging
from uuid import UUID, uuid4

from faststream import AckPolicy, Context
from faststream.rabbit import RabbitBroker, RabbitMessage, RabbitRouter

from common.enums.consumer import ConsumerName
from common.enums.payment_status import PaymentStatusType
from common.enums.queue import QueueName
from common.enums.subject import SubjectType
from common.models.events.payment import PaymentCreatedEvent
from common.services import broker_client
from config import settings
from services.gateway import emulate_payment_gateway
from services.payments import (
    get_payment,
    mark_webhook_failed,
    mark_webhook_succeeded,
    record_webhook_attempt,
    set_payment_processed,
)
from services.webhook import send_payment_webhook

logger = logging.getLogger(__name__)
router = RabbitRouter()


@router.subscriber(
    broker_client.PAYMENTS_QUEUE,
    exchange=broker_client.PAYMENTS_EXCHANGE,
    ack_policy=AckPolicy.MANUAL,
)
async def handle_payment_created(
    event: PaymentCreatedEvent,
    msg: RabbitMessage,
    broker: RabbitBroker = Context("broker"),
) -> None:
    try:
        await process_payment(event.payment_id)
    except Exception as exc:
        await retry_or_dead_letter(event, msg, broker, exc)
        return

    await msg.ack()


async def process_payment(payment_id: UUID) -> None:
    payment = await get_payment(payment_id)
    if payment is None:
        raise ValueError(f"Payment {payment_id} not found")

    if payment.webhook_sent_at is not None:
        return

    if payment.status == PaymentStatusType.pending:
        gateway_status = await emulate_payment_gateway()
        await set_payment_processed(payment_id, gateway_status)

    payment = await record_webhook_attempt(payment_id)

    try:
        await send_payment_webhook(payment)
    except Exception as exc:
        await mark_webhook_failed(payment_id, repr(exc))
        raise

    await mark_webhook_succeeded(payment_id)


async def retry_or_dead_letter(
    event: PaymentCreatedEvent,
    msg: RabbitMessage,
    broker: RabbitBroker,
    exc: Exception,
) -> None:
    attempt = current_attempt(msg)
    if attempt >= settings.consumer_max_attempts:
        logger.exception(
            "Payment message failed after %s attempts; rejecting to DLQ",
            attempt,
            exc_info=exc,
        )
        await msg.reject(requeue=False)
        return

    next_attempt = attempt + 1
    delay = settings.retry_base_delay_seconds * (2 ** (attempt - 1))
    headers = dict(msg.headers or {})
    headers["x-attempt"] = next_attempt
    headers["x-consumer"] = ConsumerName.PAYMENT_PROCESSOR
    headers["x-last-error"] = repr(exc)[:500]

    try:
        await broker.publish(
            event.model_dump(mode="json"),
            queue=QueueName.PAYMENTS_RETRY,
            headers=headers,
            expiration=delay,
            persist=True,
            message_id=f"{msg.message_id or uuid4()}:attempt:{next_attempt}",
            correlation_id=str(event.payment_id),
            message_type=SubjectType.PAYMENT_CREATED,
        )
    except Exception:
        logger.exception("Failed to publish retry message; nacking original")
        await msg.nack()
        return

    await msg.ack()


def current_attempt(msg: RabbitMessage) -> int:
    raw_attempt = (msg.headers or {}).get("x-attempt", 1)
    try:
        attempt = int(raw_attempt)
    except (TypeError, ValueError):
        return 1
    return max(attempt, 1)
