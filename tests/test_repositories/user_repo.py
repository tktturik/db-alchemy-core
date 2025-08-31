from test_models.user import TestUser

from dbalchemycore import BaseRepository


class TestUserRepo(BaseRepository):
    model = TestUser

    @classmethod
    async def get_user_orm(cls, id: int):
        user_dict = await cls.get_one(id)
        return TestUser(**user_dict)
