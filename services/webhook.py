import httpx

from common.database.schemas.payment import Payment
from common.models.payment import PaymentDetail
from config import settings


async def send_payment_webhook(payment: Payment) -> None:
    payload = PaymentDetail.from_payment(payment).model_dump(mode="json")
    async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
        response = await client.post(payment.webhook_url, json=payload)
        response.raise_for_status()
