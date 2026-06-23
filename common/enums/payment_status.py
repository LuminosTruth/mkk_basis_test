from common.enums.base_enum import BaseEnum


class PaymentStatusType(BaseEnum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
