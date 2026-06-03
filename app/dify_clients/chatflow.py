import requests
import json
import time
from typing import Optional, Dict, Any
from app.config import settings


class DifyChatflowClient:
    def __init__(self):
        self.api_key = settings.dify_api_key
        self.base_url = settings.dify_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        query: str,
        user: str,
        conversation_id: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat-messages"
        data = {
            "query": query,
            "user": user,
            "response_mode": "blocking",
            "inputs": inputs or {},
        }
        if conversation_id:
            data["conversation_id"] = conversation_id
        start_time = time.time()
        try:
            resp = requests.post(url, headers=self.headers, json=data, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": True,
                "result": result,
                "status_code": resp.status_code,
                "duration_ms": duration_ms,
                "request_body": json.dumps(data, ensure_ascii=False),
                "response_body": json.dumps(result, ensure_ascii=False),
                "error_message": None,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "result": None,
                "status_code": None,
                "duration_ms": duration_ms,
                "request_body": json.dumps(data, ensure_ascii=False) if "data" in locals() else None,
                "response_body": None,
                "error_message": str(e),
            }
