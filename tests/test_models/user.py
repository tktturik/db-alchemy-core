from sqlalchemy.orm import Mapped, mapped_column

from dbalchemycore import Base
from dbalchemycore.models import id_field


class TestUser(Base):
    id: Mapped[id_field]
    name: Mapped[str]
    surname: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
