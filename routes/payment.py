from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from common.models.payment import PaymentAccepted, PaymentCreate, PaymentDetail
from common.services.auth import require_idempotency_key
from routes.base_route import private_router
from services.payments import create_payment, get_payment


@private_router.post(
    "/payments/create",
    response_model=PaymentAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_payment_endpoint(
    payload: PaymentCreate,
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> PaymentAccepted:
    payment = await create_payment(payload, idempotency_key)
    return PaymentAccepted.from_payment(payment)


@private_router.get("/payments/{payment_id}", response_model=PaymentDetail)
async def get_payment_endpoint(payment_id: UUID) -> PaymentDetail:
    payment = await get_payment(payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return PaymentDetail.from_payment(payment)
