import pytest
from dbalchemycore import init_db
from dbalchemycore.core.database import get_session
from sqlalchemy import text

@pytest.mark.asyncio
async def test_init_db_creates_functional_connection():
    """
    Тестируем что после init_db можно установить соединение с БД
    и выполнять запросы через публичный интерфейс.
    """
    # Act
    await init_db(migrations_path="tests/migrations")
    
    # Assert - проверяем РАБОТОСПОСОБНОСТЬ через get_session
    async with get_session() as session:
        # Выполняем простой SQL запрос
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
