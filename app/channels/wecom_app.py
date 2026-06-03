import json
import time
import hashlib
import base64
import requests
from Crypto.Cipher import AES
from typing import Optional, Dict, Any
from app.config import settings


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
        decrypted = decrypted[:-pad]
        msg_len = int.from_bytes(decrypted[16:20], byteorder="big")
        msg = decrypted[20 : 20 + msg_len].decode("utf-8")
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
            if sha1.hexdigest() != msg_signature:
                return None
            msg = self._decrypt(encrypt)
            return json.loads(msg)
        except Exception:
            return None

    def send_text_message(
        self, to_user: str, content: str, to_party: Optional[str] = None, to_tag: Optional[str] = None
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
        data = {k: v for k, v in data.items() if v is not None}
        resp = requests.post(url, json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
