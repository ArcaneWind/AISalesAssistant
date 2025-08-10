from pydantic_settings import BaseSettings
from typing import Optional
from enum import Enum


class Environment(str, Enum):

    """运行环境枚举"""
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):

    # 应用基础配置
    app_name: str = "AI Sales Assistant"
    app_version: str = "1.0.0"
    environment: Environment = Environment.TESTING
    debug: bool = True
    secret_key: str = "secret-key-change-in-production"

    # 数据库配置
    database_url: Optional[str] = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "ai_sales_db"
    db_user: str = "ai_sales_user"
    db_password: str = "ai_sales_password"

    # Redis配置 (会话缓存 + Celery broker)
    redis_url: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    # Qdrant向量数据库配置
    qdrant_url: str = "http://localhost:6333"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_collection_name: str = "course_knowledge"

    # LLM服务配置
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"

    # DeepSeek配置 (轻量模型)
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 默认LLM提供商选择
    default_llm_provider: str = "openai"  # openai, deepseek

    # LLM通用配置
    llm_max_tokens: int = 2000
    llm_temperature: float = 0.7
    llm_timeout: int = 60

    # 日志配置
    log_level: str = "INFO"

    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def database_url_computed(self) -> str:
        """计算数据库URL"""
        if self.database_url:
            return self.database_url
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url_computed(self) -> str:
        """计算Redis URL"""
        if self.redis_url:
            return self.redis_url
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()