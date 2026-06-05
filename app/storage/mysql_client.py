import logging
from typing import Optional, Dict, Any
from datetime import datetime

import pymysql
import pymysql.cursors

from app.config import settings, BASE_DIR
from app.storage.base import BaseStorage

logger = logging.getLogger(__name__)


class MySQLClient(BaseStorage):
    def __init__(self):
        self._conn_kwargs = dict(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
        self._init_db()

    def _get_connection(self) -> pymysql.Connection:
        return pymysql.connect(**self._conn_kwargs)

    def _init_db(self):
        init_kwargs = {k: v for k, v in self._conn_kwargs.items() if k != "database"}
        conn = pymysql.connect(**init_kwargs)
        try:
            with conn.cursor() as cursor:
                    cursor.execute(
                        f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` "
                        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                conn.select_db(settings.mysql_database)
                with conn.cursor() as cursor:
                    init_sql = BASE_DIR / "sql" / "init_mysql.sql"
                    with open(str(init_sql), "r", encoding="utf-8") as f:
                    for stmt in f.read().split(";"):
                        stmt = stmt.strip()
                        if stmt:
                            cursor.execute(stmt)
        finally:
            conn.close()

    def get_or_create_conversation(
        self,
        session_key: str,
        channel_type: str,
        corp_id: str,
        agent_id: str,
        external_user_id: str,
        chat_id: str,
        chat_type: str,
    ) -> Dict[str, Any]:
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM conversations WHERE session_key = %s",
                    (session_key,),
                )
                row = cursor.fetchone()
                if row:
                    return row
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """
                    INSERT INTO conversations
                    (session_key, channel_type, corp_id, agent_id, external_user_id,
                     chat_id, chat_type, created_at, updated_at, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session_key,
                        channel_type,
                        corp_id,
                        agent_id,
                        external_user_id,
                        chat_id,
                        chat_type,
                        now,
                        now,
                        True,
                    ),
                )
        return self.get_conversation(session_key)

    def get_conversation(self, session_key: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM conversations WHERE session_key = %s",
                    (session_key,),
                )
                return cursor.fetchone()

    def update_conversation_dify_id(
        self, session_key: str, dify_conversation_id: str
    ):
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """
                    UPDATE conversations
                    SET dify_conversation_id = %s, updated_at = %s,
                        last_message_at = %s, message_count = message_count + 1
                    WHERE session_key = %s
                    """,
                    (dify_conversation_id, now, now, session_key),
                )

    def update_conversation_last_message(self, session_key: str):
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """
                    UPDATE conversations
                    SET updated_at = %s, last_message_at = %s,
                        message_count = message_count + 1
                    WHERE session_key = %s
                    """,
                    (now, now, session_key),
                )

    def add_message(
        self,
        session_key: str,
        role: str,
        content: str,
        dify_message_id: Optional[str] = None,
        wecom_msg_id: Optional[str] = None,
        raw_content: Optional[str] = None,
    ):
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """
                    INSERT INTO messages
                    (session_key, dify_message_id, wecom_msg_id, role, content,
                     raw_content, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session_key,
                        dify_message_id,
                        wecom_msg_id,
                        role,
                        content,
                        raw_content,
                        now,
                    ),
                )

    def add_api_log(
        self,
        endpoint: str,
        method: str,
        request_body: Optional[str] = None,
        response_body: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """
                    INSERT INTO api_logs
                    (endpoint, method, request_body, response_body, status_code,
                     duration_ms, error_message, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        endpoint,
                        method,
                        request_body,
                        response_body,
                        status_code,
                        duration_ms,
                        error_message,
                        now,
                    ),
                )
