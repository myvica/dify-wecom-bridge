from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    log_file: str = str(BASE_DIR / "data" / "app.log")

    # 企业微信配置
    wecom_corp_id: str
    wecom_app_id: str
    wecom_app_secret: str
    wecom_token: str
    wecom_encoding_aes_key: str

    # Dify 配置
    dify_api_key: str
    dify_base_url: str = "https://api.dify.ai/v1"

    # 数据库配置: sqlite 或 mysql
    db_type: str = "sqlite"

    # SQLite 配置
    sqlite_db_path: str = "./data/dify_wecom_bridge.db"

    # MySQL/MariaDB 配置
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "dify_wecom"
    mysql_password: str = ""
    mysql_database: str = "dify_wecom_bridge"

    # Redis 配置
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

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
