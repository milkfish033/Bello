"""API 配置：从环境变量加载，支持 .env 文件。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "dev"
    MODEL_BASE_URL: str = "http://localhost:8000/v1"
    MODEL_NAME: str = "deepseek-r1-lora"
    API_KEY: str = "dummy"  # 本地/内网可随便填，OpenAI/DeepSeek 等填真实 key


def get_settings() -> Settings:
    return Settings()
