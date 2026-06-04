from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseStorage(ABC):
    @abstractmethod
    def get_or_create_conversation(
        self,
        session_key: str,
        channel_type: str,
        corp_id: str,
        agent_id: str,
        external_user_id: str,
        chat_id: str,
        chat_type: str,
    ) -> Dict[str, Any]: ...

    @abstractmethod
    def get_conversation(self, session_key: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def update_conversation_dify_id(
        self, session_key: str, dify_conversation_id: str
    ): ...

    @abstractmethod
    def update_conversation_last_message(self, session_key: str): ...

    @abstractmethod
    def add_message(
        self,
        session_key: str,
        role: str,
        content: str,
        dify_message_id: Optional[str] = None,
        wecom_msg_id: Optional[str] = None,
        raw_content: Optional[str] = None,
    ): ...

    @abstractmethod
    def add_api_log(
        self,
        endpoint: str,
        method: str,
        request_body: Optional[str] = None,
        response_body: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ): ...
