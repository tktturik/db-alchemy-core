from pydantic import BaseModel
from typing import Optional

class TestUserSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    email: Optional[str] = None