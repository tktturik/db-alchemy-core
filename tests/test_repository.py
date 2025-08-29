import pytest
from test_repositories.user_repo import TestUserRepo
from test_schemas.user import TestUserSchema
from dbalchemycore.core.exc import *
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, MultipleResultsFound
from pydantic import create_model

@pytest.mark.asyncio
class TestUserRepoCRUD:
    @pytest.mark.asyncio
    async def test_create_user(self):
        user = TestUserSchema(name="Alice", surname="Bobr", email="alice@example.com")
        count = await TestUserRepo.create(values=user)
        assert count == 1
    @pytest.mark.asyncio
    async def test_get_one_user(self):
        user = await TestUserRepo.get_one(id=1)
        assert user["name"] == "Alice"
    @pytest.mark.asyncio
    async def test_update_user(self):
        update_data = TestUserSchema(name="Alice Updated", email="alice@example.com")
        count = await TestUserRepo.update(values=update_data, id=1)
        assert count == 1
    @pytest.mark.asyncio
    async def test_delete_user(self):
        count = await TestUserRepo.delete(id=1)
        assert count == 1


# Тесты на EmptyFilterError
@pytest.mark.asyncio
class TestExcEmptyFilterRepoCRUD:
    async def test_get_one_with_empty_schema(self,  empty_user):
        with pytest.raises(EmptyFilterError):
            await TestUserRepo.get_one(filters=empty_user)

    async def test_get_many_with_empty_schema(self,  empty_user):
        with pytest.raises(EmptyFilterError):
            await TestUserRepo.get_many(filters=empty_user)

    async def test_delete_with_empty_schema(self,  empty_user):
        with pytest.raises(EmptyFilterError):
            await TestUserRepo.delete(filters=empty_user)

    async def test_update_with_empty_filter(self,  empty_user):
        update_data = TestUserSchema(name="Updated")
        with pytest.raises(EmptyFilterError):
            await TestUserRepo.update(filters=empty_user, values=update_data)

# Тесты на InvalidFieldError
@pytest.mark.asyncio
class TestExcInvalidFieldRepoCRUD:
    async def test_get_one_with_invalid_field(self, schema_invalid_field):
        with pytest.raises(InvalidFieldError):
            await TestUserRepo.get_one(filters=schema_invalid_field)

    async def test_get_many_with_invalid_field(self,  schema_invalid_field):
        with pytest.raises(InvalidFieldError):
            await TestUserRepo.get_many(filters=schema_invalid_field)

    async def test_create_with_invalid_field(self,  schema_invalid_field):
        with pytest.raises(InvalidFieldError):
            await TestUserRepo.create(values=schema_invalid_field)

    async def test_update_with_invalid_field(self,  create_test_user, schema_invalid_field):
        with pytest.raises(InvalidFieldError):
            await TestUserRepo.update(values=schema_invalid_field, id=1)

    async def test_delete_with_invalid_field(self,  schema_invalid_field):
        with pytest.raises(InvalidFieldError):
            await TestUserRepo.delete(filters=schema_invalid_field)

# Тесты на UnknowAggregationFunc
@pytest.mark.asyncio
class TestExcUnknowAggregationFuncRepoCRUD:
    async def test_get_many_with_unknown_aggregation(self):
        with pytest.raises(UnknowAggregationFunc):
            await TestUserRepo.get_many(
                group_by="name",
                aggregations={"email": "invalid_func"}
            )

# Тесты на MultipleResultsFound
@pytest.mark.asyncio
class TestExcMultipleResultRepoCRUD:
    async def test_get_one_multiple_results(self, create_multiple_users):
        filters = TestUserSchema(name="Alice")
        with pytest.raises(MultipleResultsFound):
            await TestUserRepo.get_one(filters=filters, strict=True)

# Тесты на NotFoundError
@pytest.mark.asyncio
class TestExcNotFoundErrorRepoCRUD:
    async def test_get_one_not_found(self):
        with pytest.raises(NotFoundError):
            await TestUserRepo.get_one(id=999)

    async def test_delete_not_found(self):
        with pytest.raises(NotFoundError):
            await TestUserRepo.delete(id=999)

    async def test_update_not_found(self):
        update_data = TestUserSchema(name="Updated")
        with pytest.raises(NotFoundError):
            await TestUserRepo.update(values=update_data, id=999)

    async def test_get_many_not_found(self):
        filters = TestUserSchema(name="Nonexistent")
        result = await TestUserRepo.get_many(filters=filters)
        assert result == []  # get_many возвращает пустой список, а не NotFoundError

# Тесты на EmptyValueError
@pytest.mark.asyncio
class TestExcEmptyValueErrorRepoCRUD:
    async def test_update_with_empty_values(self, create_test_user):
        update_data = TestUserSchema()
        with pytest.raises(EmptyValueError):
            await TestUserRepo.update(values=update_data, id=1)

# Тесты на IntegrityError (нарушение ограничений, например, уникальности)
@pytest.mark.asyncio
class TestExcIntegrityErrorRepoCRUD:
    async def test_create_duplicate_email(self,  create_test_user):
        user = TestUserSchema(name="Bob", surname="Ablom",email="alice@example.com")  # Дубликат email
        with pytest.raises(IntegrityError):
            await TestUserRepo.create(values=user)

# Тесты на ValueError для having_filters без group_by
@pytest.mark.asyncio
class TestExcHavingWithoutGroupBy:
    async def test_get_many_having_without_group_by(self):
        having_filter = create_model('Filter',id_count=(int,5))
        with pytest.raises(ValueError):
            await TestUserRepo.get_many(having_filters=having_filter)