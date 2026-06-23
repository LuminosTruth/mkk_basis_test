from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Enum, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlmodel import Field, SQLModel

from common.enums.currency_type import CurrencyCodeType
from common.enums.payment_status import PaymentStatusType
from common.helpers import date_helper, enum_helper


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    currency: CurrencyCodeType = Field(
        sa_column=Column(
            Enum(
                CurrencyCodeType,
                name="currency_code",
                values_callable=enum_helper.enum_values,
            ),
            nullable=False,
        )
    )
    description: str = Field(sa_column=Column(String(1024), nullable=False))
    metadata_: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            "metadata",
            JSONB,
            nullable=False,
            default=dict,
            server_default=text("'{}'::jsonb"),
        ),
    )
    status: PaymentStatusType = Field(
        default=PaymentStatusType.pending,
        sa_column=Column(
            Enum(
                PaymentStatusType,
                name="payment_status",
                values_callable=enum_helper.enum_values,
            ),
            nullable=False,
            default=PaymentStatusType.pending,
            server_default=PaymentStatusType.pending,
            index=True,
        ),
    )
    idempotency_key: str = Field(
        sa_column=Column(String(255), nullable=False, unique=True, index=True)
    )
    webhook_url: str = Field(sa_column=Column(Text, nullable=False))
    webhook_attempts: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, default=0, server_default="0"),
    )
    webhook_last_error: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    webhook_sent_at: Optional[datetime] = Field(
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
    processed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
