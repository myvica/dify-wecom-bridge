from app.config import settings
from app.storage.base import BaseStorage


def create_storage() -> BaseStorage:
    if settings.db_type == "mysql":
        from app.storage.mysql_client import MySQLClient
        return MySQLClient()
    from app.storage.sqlite_client import SQLiteClient
    return SQLiteClient()
