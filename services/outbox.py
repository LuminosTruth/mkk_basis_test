from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta

from faststream.rabbit import RabbitBroker
from sqlalchemy import or_, select

from common.database.schemas.outbox import Outbox
from common.database.session import async_session_maker
from common.enums.outbox_status import OutboxStatusType
from common.enums.subject import SubjectType
from common.services import broker_client
from config import settings

logger = logging.getLogger(__name__)


class OutboxPublisher:
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="outbox-publisher")

    async def stop(self) -> None:
        if self._task is None or self._stop_event is None:
            return

        self._stop_event.set()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self._stop_event = None

    async def _run(self) -> None:
        assert self._stop_event is not None

        while not self._stop_event.is_set():
            try:
                await self.publish_pending()
            except Exception:
                logger.exception("Outbox publish cycle failed")

            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=settings.outbox_poll_interval_seconds,
                )

    async def publish_pending(self) -> int:
        now = datetime.now(UTC)
        async with async_session_maker() as session:
            result = await session.execute(
                select(Outbox)
                .where(
                    Outbox.status == OutboxStatusType.pending,
                    or_(
                        Outbox.next_attempt_at.is_(None),
                        Outbox.next_attempt_at <= now,
                    ),
                )
                .order_by(Outbox.created_at)
                .limit(settings.outbox_batch_size)
                .with_for_update(skip_locked=True)
            )
            events = list(result.scalars().all())
            if not events:
                return 0

            for event in events:
                await self._publish_event(event)

            await session.commit()
            return len(events)

    async def _publish_event(self, event: Outbox) -> None:
        try:
            await self._broker.publish(
                event.payload,
                exchange=broker_client.PAYMENTS_EXCHANGE,
                routing_key=SubjectType.PAYMENT_CREATED,
                persist=True,
                message_id=str(event.id),
                correlation_id=str(event.aggregate_id),
                message_type=event.event_type,
            )
        except Exception as exc:
            event.attempts += 1
            event.last_error = repr(exc)[:2000]

            if event.attempts >= settings.outbox_max_attempts:
                event.status = OutboxStatusType.failed
                event.next_attempt_at = None
                return

            delay = settings.outbox_base_delay_seconds * (2 ** (event.attempts - 1))
            event.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay)
            return

        event.mark_published()
