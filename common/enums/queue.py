from common.enums.base_enum import BaseEnum


class QueueName(BaseEnum):
    PAYMENTS_NEW = "payments.new"
    PAYMENTS_RETRY = "payments.retry"
    PAYMENTS_DLQ = "payments.dlq"
