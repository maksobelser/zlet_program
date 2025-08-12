# backend/config.py

from typing import List, Union
from pydantic import Field, AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    cors_origins: str = Field(..., env="CORS_ORIGINS")

    database_url: str   = Field(..., env="DATABASE_URL")
    secret: str         = Field(..., env="SECRET")
    admin_user: str     = Field(..., env="ADMIN_USER")
    admin_pass: str     = Field(..., env="ADMIN_PASS")

    application_start: str = Field(..., env="APPLICATION_START")
    application_end:   str = Field(..., env="APPLICATION_END")
    max_capacity:      int  = Field(..., env="MAX_CAPACITY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()