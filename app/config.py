from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # 企业微信配置
    wecom_corp_id: str
    wecom_app_id: str
    wecom_app_secret: str
    wecom_token: str
    wecom_encoding_aes_key: str

    # Dify 配置
    dify_api_key: str
    dify_base_url: str = "https://api.dify.ai/v1"

    # Redis 配置
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # SQLite 配置
    sqlite_db_path: str = "./data/dify_wecom_bridge.db"

    class Config:
        env_file = ".env"
        case_sensitive = False


class _SettingsProxy:
    _instance: Optional[Settings] = None

    def __getattr__(self, name):
        if self._instance is None:
            self._instance = Settings()
        return getattr(self._instance, name)


settings = _SettingsProxy()
