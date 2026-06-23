from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
_async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


def async_session_maker() -> AsyncSession:
    return _async_session_factory()


async def dispose_database() -> None:
    await engine.dispose()
