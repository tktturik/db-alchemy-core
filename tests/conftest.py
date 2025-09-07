import pytest
from pydantic import create_model
from test_repository import TestUserRepo
from test_schemas.user import TestUserSchema

from dbalchemycore import Base, init_db


@pytest.hookimpl(tryfirst=True)
def pytest_exception_interact(node, call, report):
    """
    Перехватывает и фильтрует трассировку исключений в отчетах pytest.
    Удаляет из трассировки записи, относящиеся к файлам в site-packages, чтобы упростить чтение стека вызовов.
    """
    longrepr = report.longrepr

    if isinstance(longrepr, str):
        return

    if hasattr(longrepr, "reprtraceback"):
        tb = longrepr.reprtraceback
        tb.reprentries = [
            entry
            for entry in tb.reprentries
            if "site-packages" not in entry.reprfileloc.path
        ]


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """
    Настраивает тестовую базу данных перед выполнением тестов и очищает её после.
    Инициализирует базу данных перед тестами и удаляет все таблицы после завершения сессии.
    """
    await init_db(use_create_all=True)
    yield
    from dbalchemycore.core.database import _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def create_test_user():
    """
    Создает тестового пользователя для использования в тестах.
    Создает пользователя с заданными данными, предоставляет его для теста и удаляет после завершения.
    """
    user_data = TestUserSchema(
        name="Alice", surname="Chehova", email="alice@example.com"
    )
    await TestUserRepo.create(values=user_data)
    yield user_data
    await TestUserRepo.delete(filters=user_data)


@pytest.fixture
async def create_multiple_users():
    """
    Создает несколько тестовых пользователей для использования в тестах.
    Создает двух пользователей с одинаковыми именами, но разными email, и возвращает их список.
    """
    users = [
        TestUserSchema(
            name="Alice", surname="Chehova", email="alice1@example.com"
        ),
        TestUserSchema(
            name="Alice", surname="Chehova", email="alice2@example.com"
        ),
    ]
    await TestUserRepo.create(values=users)
    return users


@pytest.fixture
async def empty_user():
    """
    Предоставляет пустую схему пользователя для тестирования сценариев с пустыми фильтрами.
    Возвращает экземпляр TestUserSchema без заполненных полей.
    """
    return TestUserSchema()


@pytest.fixture
async def schema_invalid_field():
    """
    Предоставляет схему с недопустимым полем для тестирования обработки ошибок InvalidFieldError.
    Создает и возвращает Pydantic-модель с полем 'invalid_field'.
    """
    InvalidFieldSchema = create_model("InvalidField", invalid_field=(str, ...))
    return InvalidFieldSchema(invalid_field="invalid")
