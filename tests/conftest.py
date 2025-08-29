import pytest
from dbalchemycore import init_db
from dbalchemycore import Base
from test_schemas.user import TestUserSchema
from pydantic import create_model
from test_repository import TestUserRepo

# Инициализация БД один раз
@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    await init_db()
    yield
    from dbalchemycore.core.database import _engine
    # После всех тестов — удалить таблицы
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
# Фикстура для создания тестового пользователя
@pytest.fixture
async def create_test_user():
    user_data = TestUserSchema(name="Alice", surname="Chehova", email="alice@example.com")
    await TestUserRepo.create(values=user_data)
    yield user_data
    await TestUserRepo.delete(filters=user_data)

# Фикстура для создания нескольких пользователей (для MultipleResultsFound)
@pytest.fixture
async def create_multiple_users():
    users = [
        TestUserSchema(name="Alice", surname="Chehova",email="alice1@example.com"),
        TestUserSchema(name="Alice", surname="Chehova",email="alice2@example.com")
    ]
    await TestUserRepo.create(values=users)
    return users

# Фикстура для пустой схемы
@pytest.fixture
async def empty_user():
    return TestUserSchema()

@pytest.fixture
async def schema_invalid_field():
    InvalidFieldSchema = create_model('InvalidField', invalid_field=(str, ...))
    return InvalidFieldSchema(invalid_field="invalid")