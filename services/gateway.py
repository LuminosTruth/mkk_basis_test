import asyncio
import random

from common.enums.payment_status import PaymentStatusType


async def emulate_payment_gateway() -> PaymentStatusType:
    await asyncio.sleep(random.uniform(2.0, 5.0))
    if random.random() < 0.9:
        return PaymentStatusType.succeeded
    return PaymentStatusType.failed
