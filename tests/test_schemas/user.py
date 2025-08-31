from typing import Optional

from pydantic import BaseModel


class TestUserSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    email: Optional[str] = None
