import pytest
from sqlalchemy import text

from dbalchemycore import init_db
from dbalchemycore.core.database import get_session


@pytest.mark.asyncio
async def test_init_db_creates_functional_connection():
    """
    Тестируем что после init_db можно установить соединение с БД
    и выполнять запросы через публичный интерфейс.
    """
    await init_db(use_create_all=True)

    async with get_session() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
