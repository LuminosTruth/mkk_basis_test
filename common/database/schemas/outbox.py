from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlmodel import Field, SQLModel

from common.enums.outbox_status import OutboxStatusType
from common.helpers import date_helper, enum_helper


class Outbox(SQLModel, table=True):
    __tablename__ = "outbox"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    aggregate_type: str = Field(sa_column=Column(String(64), nullable=False))
    aggregate_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), nullable=False, index=True)
    )
    event_type: str = Field(sa_column=Column(String(128), nullable=False))
    payload: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    status: OutboxStatusType = Field(
        default=OutboxStatusType.pending,
        sa_column=Column(
            Enum(
                OutboxStatusType,
                name="outbox_status",
                values_callable=enum_helper.enum_values,
            ),
            nullable=False,
            default=OutboxStatusType.pending,
            server_default=OutboxStatusType.pending,
            index=True,
        ),
    )
    attempts: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, default=0, server_default="0"),
    )
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    next_attempt_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=date_helper.utc_now,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=date_helper.utc_now,
            server_default=func.now(),
        ),
    )
    published_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def mark_published(self) -> None:
        self.status = OutboxStatusType.published
        self.published_at = date_helper.utc_now()
        self.last_error = None
