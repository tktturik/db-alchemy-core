import pytest
from pydantic import create_model
from sqlalchemy.exc import IntegrityError, MultipleResultsFound
from test_repositories.user_repo import TestUserRepo
from test_schemas.user import TestUserSchema

from dbalchemycore.core.exc import (
    EmptyFilterError,
    EmptyValueError,
    InvalidFieldError,
    NotFoundError,
    UnknowAggregationFunc,
)


@pytest.mark.asyncio
class TestUserRepoCRUD:
    @pytest.mark.asyncio
    async def test_create_user(self):
        """
        Тестирует создание нового пользователя в репозитории.
        Проверяет, что метод create возвращает 1 при успешном создании пользователя.
        """
        user = TestUserSchema(
            name="Alice", surname="Bobr", email="alice@example.com"
        )
        count = await TestUserRepo.create(values=user)
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_one_user(self):
        """
        Тестирует получение одного пользователя по ID.
        Проверяет, что имя возвращенного пользователя соответствует ожидаемому.
        """
        user = await TestUserRepo.get_one(id=1)
        assert user["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_update_user(self):
        """
        Тестирует обновление данных пользователя.
        Проверяет, что метод update возвращает 1 при успешном обновлении.
        """
        update_data = TestUserSchema(
            name="Alice Updated", email="alice@example.com"
        )
        count = await TestUserRepo.update(values=update_data, id=1)
        assert count == 1

    @pytest.mark.asyncio
    async def test_delete_user(self):
        """
        Тестирует удаление пользователя по ID.
        Проверяет, что метод delete возвращает 1 при успешном удалении.
        """
        count = await TestUserRepo.delete(id=1)
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_one_not_found(self):
        """
        Тестирует получение пользователя по несуществующему ID.
        Проверяет, что метод get_one возвращает None, если пользователь не найден.
        """
        res = await TestUserRepo.get_one(id=999)
        assert res is None


@pytest.mark.asyncio
class TestExcEmptyFilterRepoCRUD:
    async def test_get_one_with_empty_schema(self, empty_user):
        """
        Тестирует вызов get_one с пустым фильтром.
        Проверяет, что выбрасывается исключение EmptyFilterError.
        """
        with pytest.raises(EmptyFilterError):
            await TestUserRepo.get_one(filters=empty_user)

    async def test_get_many_with_empty_schema(self, empty_user):
        """
        Тестирует вызов get_many с пустым фильтром.
        Проверяет, что выбрасывается исключение EmptyFilterError.
        """
        with pytest.raises(EmptyFilterError):
            await TestUserRepo.get_many(filters=empty_user)

    async def test_delete_with_empty_schema(self, empty_user):
        """
        Тестирует вызов delete с пустым фильтром.
        Проверяет, что выбрасывается исключение EmptyFilterError.
        """
        with pytest.raises(EmptyFilterError):
            await TestUserRepo.delete(filters=empty_user)

    async def test_update_with_empty_filter(self, empty_user):
        """
        Тестирует вызов update с пустым фильтром.
        Проверяет, что выбрасывается исключение EmptyFilterError.
        """
        update_data = TestUserSchema(name="Updated")
        with pytest.raises(EmptyFilterError):
            await TestUserRepo.update(filters=empty_user, values=update_data)


@pytest.mark.asyncio
class TestExcInvalidFieldRepoCRUD:
    async def test_get_one_with_invalid_field(self, schema_invalid_field):
        """
        Тестирует вызов get_one с недопустимым полем в фильтре.
        Проверяет, что выбрасывается исключение InvalidFieldError.
        """
        with pytest.raises(InvalidFieldError):
            await TestUserRepo.get_one(filters=schema_invalid_field)

    async def test_get_many_with_invalid_field(self, schema_invalid_field):
        """
        Тестирует вызов get_many с недопустимым полем в фильтре.
        Проверяет, что выбрасывается исключение InvalidFieldError.
        """
        with pytest.raises(InvalidFieldError):
            await TestUserRepo.get_many(filters=schema_invalid_field)

    async def test_create_with_invalid_field(self, schema_invalid_field):
        """
        Тестирует вызов create с недопустимым полем в данных.
        Проверяет, что выбрасывается исключение InvalidFieldError.
        """
        with pytest.raises(InvalidFieldError):
            await TestUserRepo.create(values=schema_invalid_field)

    async def test_update_with_invalid_field(
        self, create_test_user, schema_invalid_field
    ):
        """
        Тестирует вызов update с недопустимым полем в данных.
        Проверяет, что выбрасывается исключение InvalidFieldError.
        """
        with pytest.raises(InvalidFieldError):
            await TestUserRepo.update(values=schema_invalid_field, id=1)

    async def test_delete_with_invalid_field(self, schema_invalid_field):
        """
        Тестирует вызов delete с недопустимым полем в фильтре.
        Проверяет, что выбрасывается исключение InvalidFieldError.
        """
        with pytest.raises(InvalidFieldError):
            await TestUserRepo.delete(filters=schema_invalid_field)


@pytest.mark.asyncio
class TestExcUnknowAggregationFuncRepoCRUD:
    async def test_get_many_with_unknown_aggregation(self):
        """
        Тестирует вызов get_many с неизвестной функцией агрегации.
        Проверяет, что выбрасывается исключение UnknowAggregationFunc.
        """
        with pytest.raises(UnknowAggregationFunc):
            await TestUserRepo.get_many(
                group_by="name", aggregations={"email": "invalid_func"}
            )


@pytest.mark.asyncio
class TestExcMultipleResultRepoCRUD:
    async def test_get_one_multiple_results(self, create_multiple_users):
        """
        Тестирует вызов get_one, когда найдено несколько результатов.
        Проверяет, что выбрасывается исключение MultipleResultsFound при strict=True.
        """
        filters = TestUserSchema(name="Alice")
        with pytest.raises(MultipleResultsFound):
            await TestUserRepo.get_one(filters=filters, strict=True)


@pytest.mark.asyncio
class TestExcNotFoundErrorRepoCRUD:
    async def test_delete_not_found(self):
        """
        Тестирует вызов delete с несуществующим ID.
        Проверяет, что выбрасывается исключение NotFoundError.
        """
        with pytest.raises(NotFoundError):
            await TestUserRepo.delete(id=999)

    async def test_update_not_found(self):
        """
        Тестирует вызов update с несуществующим ID.
        Проверяет, что выбрасывается исключение NotFoundError.
        """
        update_data = TestUserSchema(name="Updated")
        with pytest.raises(NotFoundError):
            await TestUserRepo.update(values=update_data, id=999)

    async def test_get_many_not_found(self):
        """
        Тестирует вызов get_many с фильтром, который не соответствует ни одному пользователю.
        Проверяет, что возвращается пустой список.
        """
        filters = TestUserSchema(name="Nonexistent")
        result = await TestUserRepo.get_many(filters=filters)
        assert result == []


@pytest.mark.asyncio
class TestExcEmptyValueErrorRepoCRUD:
    async def test_update_with_empty_values(self, create_test_user):
        """
        Тестирует вызов update с пустыми значениями.
        Проверяет, что выбрасывается исключение EmptyValueError.
        """
        update_data = TestUserSchema()
        with pytest.raises(EmptyValueError):
            await TestUserRepo.update(values=update_data, id=1)


@pytest.mark.asyncio
class TestExcIntegrityErrorRepoCRUD:
    async def test_create_duplicate_email(self, create_test_user):
        """
        Тестирует создание пользователя с уже существующим email.
        Проверяет, что выбрасывается исключение IntegrityError из-за нарушения уникальности.
        """
        user = TestUserSchema(
            name="Bob", surname="Ablom", email="alice@example.com"
        )
        with pytest.raises(IntegrityError):
            await TestUserRepo.create(values=user)


@pytest.mark.asyncio
class TestExcHavingWithoutGroupBy:
    async def test_get_many_having_without_group_by(self):
        """
        Тестирует вызов get_many с having-фильтром без указания group_by.
        Проверяет, что выбрасывается исключение ValueError.
        """
        having_filter = create_model("Filter", id_count=(int, 5))
        with pytest.raises(ValueError):
            await TestUserRepo.get_many(having_filters=having_filter)
