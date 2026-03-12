# app/core/config.py
import os
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dateutil import tz

class Settings(BaseSettings):
    DB_URL: str = Field(..., description="SQLAlchemy URL", env="DB_URL")
    GOOGLE_CLIENT_SECRETS_FILE: str = Field("credentials.json", env="GOOGLE_CLIENT_SECRETS_FILE")
    GOOGLE_SCOPES: list[str] = ["https://www.googleapis.com/auth/calendar"]
    OAUTH_REDIRECT_URI: str = Field("http://localhost:8000/oauth2callback", env="OAUTH_REDIRECT_URI")
    TZNAME: str = Field("Asia/Singapore", env="TZNAME")
    CORS_ALLOW_ORIGINS: list[str] = ["*"]
    OPENAI_API_KEY: str = Field(..., description="OpenAI API Key", env="OPENAI_API_KEY")

    AGENT_MODEL: str = Field("gpt-4o-mini-2024-07-18", env="AGENT_MODEL")
    AGENT_TEMPERATURE: float = Field(0.2, env="AGENT_TEMPERATURE")
    USE_LLM_PLANNER: ClassVar[bool] = True
    KNOWLEDGE_ENABLE: ClassVar[bool] = True
    KNOWLEDGE_FAKE_FALLBACK: ClassVar[bool] = True
    MEMORY_ENABLE: ClassVar[bool] = True
    MEMORY_FAKE_FALLBACK: ClassVar[bool] = True
    # === 功能开关 ===
    AGENT_ENABLE_TOOLS: bool = Field(True, env="AGENT_ENABLE_TOOLS")
    AGENT_ENABLE_RAG: bool = Field(False, env="AGENT_ENABLE_RAG")
    RAG_INDEX_DIR: str | None = Field(None, env="RAG_INDEX_DIR")
    # pydantic v2 配置方式
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

settings = Settings()
TZ = tz.gettz(settings.TZNAME)

# 本地开发允许 http 的 OAuth 回调（生产一定别开）
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
