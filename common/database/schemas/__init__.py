from sqlmodel import SQLModel

from common.database.schemas.outbox import Outbox
from common.database.schemas.payment import Payment

metadata = SQLModel.metadata

__all__ = ["Outbox", "Payment", "metadata"]

