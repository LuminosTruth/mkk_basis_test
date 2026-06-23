from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.database.schemas.outbox import Outbox
from common.database.schemas.payment import Payment
from common.database.session import async_session_maker
from common.enums.payment_status import PaymentStatusType
from common.enums.subject import SubjectType
from common.models.events.payment import PaymentCreatedEvent
from common.models.payment import PaymentCreate


async def create_payment(
    payload: PaymentCreate,
    idempotency_key: str,
) -> Payment:
    async with async_session_maker() as session:
        existing = await _get_payment_by_idempotency_key(session, idempotency_key)
        if existing is not None:
            return existing

        payment = Payment(
            amount=payload.amount,
            currency=payload.currency,
            description=payload.description,
            metadata_=payload.metadata,
            idempotency_key=idempotency_key,
            webhook_url=str(payload.webhook_url),
        )
        session.add(payment)
        await session.flush()

        event = PaymentCreatedEvent(payment_id=payment.id)
        session.add(
            Outbox(
                aggregate_type="payment",
                aggregate_id=payment.id,
                event_type=SubjectType.PAYMENT_CREATED,
                payload=event.model_dump(mode="json"),
            )
        )

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing = await _get_payment_by_idempotency_key(session, idempotency_key)
            if existing is not None:
                return existing
            raise

        await session.refresh(payment)
        return payment


async def get_payment(payment_id: UUID) -> Payment | None:
    async with async_session_maker() as session:
        return await session.get(Payment, payment_id)


async def set_payment_processed(
    payment_id: UUID,
    status: PaymentStatusType,
) -> Payment:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise ValueError(f"Payment {payment_id} not found")

        if payment.status == PaymentStatusType.pending:
            payment.status = status
            payment.processed_at = datetime.now(UTC)

        await session.commit()
        await session.refresh(payment)
        return payment


async def record_webhook_attempt(payment_id: UUID) -> Payment:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise ValueError(f"Payment {payment_id} not found")

        payment.webhook_attempts += 1
        await session.commit()
        await session.refresh(payment)
        return payment


async def mark_webhook_succeeded(payment_id: UUID) -> None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise ValueError(f"Payment {payment_id} not found")

        payment.webhook_sent_at = datetime.now(UTC)
        payment.webhook_last_error = None
        await session.commit()


async def mark_webhook_failed(payment_id: UUID, error: str) -> None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise ValueError(f"Payment {payment_id} not found")

        payment.webhook_last_error = error[:2000]
        await session.commit()


async def _get_payment_by_idempotency_key(
    session: AsyncSession,
    idempotency_key: str,
) -> Payment | None:
    result = await session.execute(
        select(Payment).where(Payment.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()
