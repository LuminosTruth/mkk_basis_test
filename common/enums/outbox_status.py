from common.enums.base_enum import BaseEnum


class OutboxStatusType(BaseEnum):
    pending = "pending"
    published = "published"
    failed = "failed"
