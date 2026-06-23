from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from common.database.schemas.payment import Payment
from common.enums.currency_type import CurrencyCodeType
from common.enums.payment_status import PaymentStatusType


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: CurrencyCodeType
    description: str = Field(default="", max_length=1024)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: AnyHttpUrl


class PaymentAccepted(BaseModel):
    payment_id: UUID
    status: PaymentStatusType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_payment(cls, payment: Payment) -> "PaymentAccepted":
        return cls(
            payment_id=payment.id,
            status=payment.status,
            created_at=payment.created_at,
        )


class PaymentDetail(BaseModel):
    payment_id: UUID
    amount: Decimal
    currency: CurrencyCodeType
    description: str
    metadata: dict[str, Any]
    status: PaymentStatusType
    idempotency_key: str
    webhook_url: str
    webhook_attempts: int
    webhook_last_error: str | None
    webhook_sent_at: datetime | None
    created_at: datetime
    processed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_payment(cls, payment: Payment) -> "PaymentDetail":
        return cls(
            payment_id=payment.id,
            amount=payment.amount,
            currency=payment.currency,
            description=payment.description,
            metadata=payment.metadata_,
            status=payment.status,
            idempotency_key=payment.idempotency_key,
            webhook_url=payment.webhook_url,
            webhook_attempts=payment.webhook_attempts,
            webhook_last_error=payment.webhook_last_error,
            webhook_sent_at=payment.webhook_sent_at,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )

