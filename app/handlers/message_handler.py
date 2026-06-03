import json
import logging
from typing import Optional, Dict, Any
from app.config import settings
from app.storage.sqlite_client import SQLiteClient
from app.storage.redis_client import RedisClient
from app.channels.wecom_app import WeComAppClient
from app.dify_clients.chatflow import DifyChatflowClient

logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(self):
        self.sqlite_client = SQLiteClient()
        self.redis_client = RedisClient()
        self.wecom_client = WeComAppClient()
        self.dify_client = DifyChatflowClient()

    def _build_session_key(
        self,
        corp_id: str, agent_id: str, chat_type: str, external_user_id: str, chat_id: str
    ) -> str:
        return f"wecom_app:{corp_id}:{agent_id}:{chat_type}:{external_user_id}:{chat_id}"

    def handle_wecom_message(self, msg_data: Dict[str, Any]) -> None:
        logger.info(f"收到企微消息: {msg_data}")
        msg_type = msg_data.get("MsgType")
        if msg_type != "text":
            logger.info(f"忽略非文本消息, MsgType={msg_type}")
            return

        corp_id = msg_data.get("ToUserName", "")
        from_user = msg_data.get("FromUserName", "")
        agent_id = msg_data.get("AgentID", "")
        content = msg_data.get("Content", "")
        msg_id = msg_data.get("MsgId", "")
        chat_type = msg_data.get("ChatType", "single")
        chat_id = msg_data.get("ChatId", "direct") if chat_type == "group" else "direct"

        session_key = self._build_session_key(
            corp_id, str(agent_id), chat_type, from_user, chat_id
        )

        conversation = self.sqlite_client.get_or_create_conversation(
            session_key=session_key,
            channel_type="wecom_app",
            corp_id=corp_id,
            agent_id=str(agent_id),
            external_user_id=from_user,
            chat_id=chat_id,
            chat_type=chat_type,
        )

        dify_conversation_id = conversation.get("dify_conversation_id")

        self.sqlite_client.add_message(
            session_key=session_key,
            role="user",
            content=content,
            wecom_msg_id=msg_id,
            raw_content=json.dumps(msg_data, ensure_ascii=False),
        )

        dify_response = self.dify_client.chat(
            query=content,
            user=session_key,
            conversation_id=dify_conversation_id,
        )

        logger.info(f"Dify响应: {dify_response}")

        self.sqlite_client.add_api_log(
            endpoint="/chat-messages",
            method="POST",
            request_body=dify_response.get("request_body"),
            response_body=dify_response.get("response_body"),
            status_code=dify_response.get("status_code"),
            duration_ms=dify_response.get("duration_ms"),
            error_message=dify_response.get("error_message"),
        )

        dify_result = dify_response.get("result", {})
        if not dify_result:
            return

        answer = dify_result.get("answer", "")
        new_dify_conversation_id = dify_result.get("conversation_id")
        dify_message_id = dify_result.get("message_id")

        if new_dify_conversation_id and new_dify_conversation_id != dify_conversation_id:
            self.sqlite_client.update_conversation_dify_id(
                session_key, new_dify_conversation_id
            )
        else:
            self.sqlite_client.update_conversation_last_message(session_key)

        self.sqlite_client.add_message(
            session_key=session_key,
            role="assistant",
            content=answer,
            dify_message_id=dify_message_id,
            raw_content=json.dumps(dify_result, ensure_ascii=False),
        )

        chat_type = msg_data.get("ChatType", "single")
        if chat_type == "single":
            logger.info(f"发送消息给用户: {from_user}, 内容: {answer[:50]}...")
            self.wecom_client.send_text_message(to_user=from_user, content=answer)
        elif chat_type == "group":
            logger.info(f"发送群消息: {from_user}, 内容: {answer[:50]}...")
            self.wecom_client.send_text_message(to_user=from_user, content=answer)
