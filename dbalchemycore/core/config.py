from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional
from pathlib import Path  # Импорт Path



class DatabaseSettings(BaseSettings):
    """
    Настройки базы данных, загружаемые из .env файла.
    
    Пример .env файла:
    DB_USER=postgres
    DB_PASSWORD=secret_password
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=mydatabase
    DB_ECHO=False
    DB_POOL_SIZE=20
    DB_MAX_OVERFLOW=50
    DB_CONNECT_TIMEOUT=10
    """
    DB_DIALECT: str = Field("postgresql")
    DB_DRIVER: str = Field("asyncpg")
    DB_USER: Optional[str] = Field(default=None)
    DB_PASSWORD: Optional[SecretStr] = Field(default=None)
    DB_HOST: str = Field("localhost")
    DB_PORT: int = Field(5432)
    DB_NAME: Optional[str] = Field(default=None)
    
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
        """
        Формирует URL для подключения к базе данных.
        
        Пример результата:
        'postgresql+asyncpg://postgres:secret_password@localhost:5432/mydatabase'
        """
        return (
            f"{self.DB_DIALECT}+{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    


settings = DatabaseSettings()