import json
import logging
from typing import Optional, Dict, Any
from app.config import settings
from app.storage import create_storage
from app.storage.redis_client import RedisClient
from app.channels.wecom_app import default_wecom_client
from app.dify_clients.chatflow import DifyChatflowClient

logger = logging.getLogger(__name__)

REDIS_CONV_TTL = 86400 * 7


class MessageHandler:
    def __init__(self):
        self.storage = create_storage()
        self.redis = RedisClient()
        self.wecom_client = default_wecom_client
        self.dify_client = DifyChatflowClient()

    def _cache_key(self, session_key: str) -> str:
        return f"conv:{session_key}"

    def _get_cached_conversation(self, session_key: str) -> Optional[dict]:
        return self.redis.get(self._cache_key(session_key))

    def _set_cached_conversation(self, session_key: str, data: dict):
        self.redis.set(self._cache_key(session_key), data, ex=REDIS_CONV_TTL)

    def _invalidate_cache(self, session_key: str):
        self.redis.delete(self._cache_key(session_key))

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

        conversation = self._get_cached_conversation(session_key)
        if not conversation:
            conversation = self.storage.get_or_create_conversation(
                session_key=session_key,
                channel_type="wecom_app",
                corp_id=corp_id,
                agent_id=str(agent_id),
                external_user_id=from_user,
                chat_id=chat_id,
                chat_type=chat_type,
            )
            self._set_cached_conversation(session_key, conversation)

        dify_conversation_id = conversation.get("dify_conversation_id")

        self.storage.add_message(
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

        logger.debug(f"Dify响应: {dify_response}")
        logger.info(f"Dify响应完成: message_id={dify_response.get('result', {}).get('message_id', 'N/A')}, status={dify_response.get('status_code')}, duration={dify_response.get('duration_ms')}ms")

        self.storage.add_api_log(
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
            logger.error(f"Dify调用失败: {dify_response.get('error_message')}")
            chat_type = msg_data.get("ChatType", "single")
            if chat_type == "single":
                self.wecom_client.send_text_message(to_user=from_user, content="服务暂时不可用，请稍后再试")
            return

        answer = dify_result.get("answer", "")
        new_dify_conversation_id = dify_result.get("conversation_id")
        dify_message_id = dify_result.get("message_id")

        if new_dify_conversation_id and new_dify_conversation_id != dify_conversation_id:
            self.storage.update_conversation_dify_id(
                session_key, new_dify_conversation_id
            )
        else:
            self.storage.update_conversation_last_message(session_key)

        updated = self.storage.get_conversation(session_key)
        self._set_cached_conversation(session_key, updated)

        self.storage.add_message(
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
