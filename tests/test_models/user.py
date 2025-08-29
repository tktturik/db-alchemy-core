from sqlalchemy.orm import Mapped, mapped_column


from dbalchemycore import Base
class TestUser(Base):
    name: Mapped[str]
    surname: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
