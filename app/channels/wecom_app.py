import json
import time
import hashlib
import base64
import logging
import xml.etree.ElementTree as ET
import requests
from Crypto.Cipher import AES
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)


class WeComAppClient:
    def __init__(self):
        self.corp_id = settings.wecom_corp_id
        self.app_id = settings.wecom_app_id
        self.app_secret = settings.wecom_app_secret
        self.token = settings.wecom_token
        self.encoding_aes_key = settings.wecom_encoding_aes_key
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    def _get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            return self._access_token
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.app_secret,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errcode") != 0:
            raise Exception(f"获取 access_token 失败: {data}")
        self._access_token = data["access_token"]
        self._token_expires_at = now + data["expires_in"] - 300
        return self._access_token

    def _decrypt(self, encrypt: str) -> str:
        aes_key = base64.b64decode(self.encoding_aes_key + "=")
        iv = aes_key[:16]
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(base64.b64decode(encrypt))
        pad = decrypted[-1]
        if pad < 1 or pad > 32:
            raise ValueError(f"无效的PKCS7填充值: {pad}")
        if decrypted[-pad:] != bytes([pad]) * pad:
            raise ValueError("PKCS7填充校验失败")
        decrypted = decrypted[:-pad]
        msg_len = int.from_bytes(decrypted[16:20], byteorder="big")
        msg = decrypted[20 : 20 + msg_len].decode("utf-8")
        receive_id = decrypted[20 + msg_len:].decode("utf-8")
        if receive_id != self.corp_id:
            raise ValueError(f"接收方ID不匹配: 期望 {self.corp_id}, 实际 {receive_id}")
        return msg

    def _encrypt(self, msg: str) -> str:
        import struct
        import random
        import string
        aes_key = base64.b64decode(self.encoding_aes_key + "=")
        iv = aes_key[:16]
        random_str = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        msg_bytes = msg.encode("utf-8")
        msg_len = struct.pack(">I", len(msg_bytes))
        corp_id_bytes = self.corp_id.encode("utf-8")
        full_msg = random_str.encode("utf-8") + msg_len + msg_bytes + corp_id_bytes
        pad = 32 - (len(full_msg) % 32)
        full_msg += bytes([pad]) * pad
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(full_msg)
        return base64.b64encode(encrypted).decode("utf-8")

    def verify_url(
        self, msg_signature: str, timestamp: str, nonce: str, echostr: str
    ) -> Optional[str]:
        try:
            sort_list = sorted([self.token, timestamp, nonce, echostr])
            sha1 = hashlib.sha1()
            for s in sort_list:
                sha1.update(s.encode("utf-8"))
            if sha1.hexdigest() != msg_signature:
                return None
            return self._decrypt(echostr)
        except Exception:
            return None

    def decrypt_message(
        self, msg_signature: str, timestamp: str, nonce: str, encrypt: str
    ) -> Optional[Dict[str, Any]]:
        try:
            sort_list = sorted([self.token, timestamp, nonce, encrypt])
            sha1 = hashlib.sha1()
            for s in sort_list:
                sha1.update(s.encode("utf-8"))
            calculated_signature = sha1.hexdigest()
            logger.info(f"签名验证 - 计算值: {calculated_signature}, 接收值: {msg_signature}")
            if calculated_signature != msg_signature:
                logger.warning(f"签名不匹配! Token: {self.token[:6]}...")
                return None
            msg = self._decrypt(encrypt)
            logger.info(f"解密成功: {msg[:100]}...")
            root = ET.fromstring(msg)
            result = {}
            for child in root:
                result[child.tag] = child.text
            return result
        except Exception as e:
            logger.error(f"解密异常: {e}")
            return None

    def send_text_message(
        self, to_user: str, content: str, to_party: Optional[str] = None, to_tag: Optional[str] = None, chatid: Optional[str] = None
    ) -> Dict[str, Any]:
        access_token = self._get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        data = {
            "touser": to_user,
            "toparty": to_party,
            "totag": to_tag,
            "msgtype": "text",
            "agentid": int(self.app_id),
            "text": {"content": content},
            "safe": 0,
        }
        if chatid:
            data["chatid"] = chatid
        data = {k: v for k, v in data.items() if v is not None}
        logger.info(f"发送企微消息: touser={to_user}, agentid={self.app_id}, chatid={chatid}")
        resp = requests.post(url, json=data, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"企微发送结果: {result}")
        return result

    def send_markdown_message(
        self, to_user: str, content: str, to_party: Optional[str] = None, to_tag: Optional[str] = None, chatid: Optional[str] = None
    ) -> Dict[str, Any]:
        access_token = self._get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        data = {
            "touser": to_user,
            "toparty": to_party,
            "totag": to_tag,
            "msgtype": "markdown",
            "agentid": int(self.app_id),
            "markdown": {"content": content},
        }
        if chatid:
            data["chatid"] = chatid
        data = {k: v for k, v in data.items() if v is not None}
        logger.info(f"发送企微Markdown消息: touser={to_user}, agentid={self.app_id}, chatid={chatid}")
        resp = requests.post(url, json=data, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"企微Markdown发送结果: {result}")
        return result


default_wecom_client = WeComAppClient()
