from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
import logging
from app.channels.wecom_app import default_wecom_client
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["send"])


class SendRequest(BaseModel):
    content: str = Field(..., description="消息内容")
    to_user: str = Field(..., description="接收人 userid，多个用 | 分隔")
    msg_type: Literal["text", "markdown"] = Field(default="markdown", description="消息类型")
    to_party: Optional[str] = Field(default=None, description="部门 ID，多个用 | 分隔")
    to_tag: Optional[str] = Field(default=None, description="标签 ID，多个用 | 分隔")


def verify_api_key(authorization: Optional[str]) -> None:
    api_key = settings.bridge_api_key
    if not api_key:
        return
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization 头")
    token = authorization.removeprefix("Bearer ").strip()
    if token != api_key:
        raise HTTPException(status_code=403, detail="API Key 无效")


@router.post("/send")
async def send_message(
    req: SendRequest,
    authorization: Optional[str] = Header(default=None),
):
    verify_api_key(authorization)

    logger.info(f"收到发送请求: to_user={req.to_user}, msg_type={req.msg_type}, content_len={len(req.content)}")

    try:
        if req.msg_type == "markdown":
            result = default_wecom_client.send_markdown_message(
                to_user=req.to_user,
                content=req.content,
                to_party=req.to_party,
                to_tag=req.to_tag,
            )
        else:
            result = default_wecom_client.send_text_message(
                to_user=req.to_user,
                content=req.content,
                to_party=req.to_party,
                to_tag=req.to_tag,
            )
    except Exception as e:
        logger.exception("发送消息异常")
        raise HTTPException(status_code=500, detail=f"发送失败: {e}")

    errcode = result.get("errcode", -1)
    if errcode != 0:
        raise HTTPException(status_code=502, detail=f"企微返回错误: {result}")

    return result
