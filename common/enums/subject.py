from common.enums.base_enum import BaseEnum


class SubjectType(BaseEnum):
    PAYMENT_ALL = "payment.>"
    PAYMENT_CREATED = "payment.created"
