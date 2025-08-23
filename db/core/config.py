from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from pathlib import Path  # Импорт Path



class DatabaseSettings(BaseSettings):
    DB_DIALECT: str = Field("postgresql")
    DB_DRIVER: str = Field("asyncpg")
    DB_USER: str
    DB_PASSWORD: SecretStr  # Безопасное хранение
    DB_HOST: str = Field("localhost")
    DB_PORT: int = Field(5432)
    DB_NAME: str
    
    # Настройки движка
    DB_ECHO: bool = Field(True)
    DB_POOL_SIZE: int = Field(5)
    DB_MAX_OVERFLOW: int = Field(10)
    DB_CONNECT_TIMEOUT: int = Field(30)

    
    # Настройки .env файла
    model_config = SettingsConfigDict(
        env_file=Path(".env"),  # Автоматически ищет .env в корне приложения
        env_file_encoding="utf-8",
        extra="ignore"  # Игнорирует переменные, которые не указаны в классе
    )
    
    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"{self.DB_DIALECT}+{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    


settings = DatabaseSettings()