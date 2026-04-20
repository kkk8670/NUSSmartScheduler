import os
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dateutil import tz

class Settings(BaseSettings):
    # Pydantic V2 会自动匹配环境变量名（如 DB_URL 对应环境变量 DB_URL）
    # 如果变量名和环境变量名完全一致，不需要写 env="xxx"
    DB_URL: str = Field(..., description="SQLAlchemy URL")
    GOOGLE_CLIENT_SECRETS_FILE: str = "credentials.json"
    GOOGLE_SCOPES: list[str] = ["https://www.googleapis.com/auth/calendar"]
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/oauth2callback"
    TZNAME: str = "Asia/Singapore"
    CORS_ALLOW_ORIGINS: list[str] = ["*"]
    OPENAI_API_KEY: str = Field(..., description="OpenAI API Key")

    AGENT_MODEL: str = "gpt-4o-mini-2024-07-18"
    AGENT_TEMPERATURE: float = 0.2
    
    USE_LLM_PLANNER: ClassVar[bool] = True
    KNOWLEDGE_ENABLE: ClassVar[bool] = True
    KNOWLEDGE_FAKE_FALLBACK: ClassVar[bool] = True
    MEMORY_ENABLE: ClassVar[bool] = True
    MEMORY_FAKE_FALLBACK: ClassVar[bool] = True
    
    # === 功能开关 ===
    AGENT_ENABLE_TOOLS: bool = True
    AGENT_ENABLE_RAG: bool = False
    RAG_INDEX_DIR: str | None = None
    
    # === Weaviate ===
    WEAVIATE_HOST: str = "localhost"
    WEAVIATE_HTTP_PORT: int = 8080
    WEAVIATE_GRPC_PORT: int = 50051
    
    # === Langfuse 配置 ===
    # 使用 validation_alias 兼容不同的环境变量名映射
    LANGFUSE_PUBLIC_KEY: str | None = Field(None, validation_alias="LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY: str | None = Field(None, validation_alias="LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST: str = Field("https://us.cloud.langfuse.com", validation_alias="LANGFUSE_BASE_URL")

    # pydantic v2 配置方式
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # 如果你想强制大小写不敏感匹配环境变量，可以加上这行
        env_ignore_empty=True
    )

settings = Settings()
TZ = tz.gettz(settings.TZNAME)

# 本地开发允许 http 的 OAuth 回调
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")