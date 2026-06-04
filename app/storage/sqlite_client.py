import sqlite3
import os
from typing import Optional, Dict, Any
from datetime import datetime
from app.config import settings
from app.storage.base import BaseStorage


class SQLiteClient(BaseStorage):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.sqlite_db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            with open("sql/init.sql", "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM conversations WHERE session_key = ?",
                (session_key,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO conversations
                (session_key, channel_type, corp_id, agent_id, external_user_id, chat_id, chat_type, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.commit()
            return self.get_conversation(session_key)

    def get_conversation(self, session_key: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM conversations WHERE session_key = ?",
                (session_key,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_conversation_dify_id(
        self, session_key: str, dify_conversation_id: str
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE conversations
                SET dify_conversation_id = ?, updated_at = ?, last_message_at = ?, message_count = message_count + 1
                WHERE session_key = ?
                """,
                (dify_conversation_id, now, now, session_key),
            )
            conn.commit()

    def update_conversation_last_message(self, session_key: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE conversations
                SET updated_at = ?, last_message_at = ?, message_count = message_count + 1
                WHERE session_key = ?
                """,
                (now, now, session_key),
            )
            conn.commit()

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
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO messages
                (session_key, dify_message_id, wecom_msg_id, role, content, raw_content, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
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
            conn.commit()

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
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO api_logs
                (endpoint, method, request_body, response_body, status_code, duration_ms, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.commit()
