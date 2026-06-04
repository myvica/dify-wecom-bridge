from fastapi import APIRouter, Request, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse
import xml.etree.ElementTree as ET
import logging
from app.channels.wecom_app import default_wecom_client
from app.handlers.message_handler import MessageHandler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wecom", tags=["wecom"])
wecom_client = default_wecom_client
message_handler = MessageHandler()


@router.get("/callback", response_class=PlainTextResponse)
async def verify_url(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    logger.info(f"收到URL验证请求: msg_signature={msg_signature}, timestamp={timestamp}, nonce={nonce}")
    result = wecom_client.verify_url(msg_signature, timestamp, nonce, echostr)
    if result:
        logger.info(f"URL验证成功, 返回echostr")
        return PlainTextResponse(content=result)
    logger.warning("URL验证失败")
    return PlainTextResponse(content="fail", status_code=403)


@router.post("/callback", response_class=PlainTextResponse)
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
):
    try:
        logger.info(f"收到消息回调: msg_signature={msg_signature}")
        body = await request.body()
        logger.debug(f"回调原始数据: {body}")
        root = ET.fromstring(body)
        encrypt = root.findtext("Encrypt", "")
        msg_data = wecom_client.decrypt_message(msg_signature, timestamp, nonce, encrypt)
        if msg_data:
            logger.info(f"消息解密成功: {msg_data}")
            background_tasks.add_task(message_handler.handle_wecom_message, msg_data)
        else:
            logger.warning("消息解密失败")
    except Exception:
        logger.exception("处理回调消息异常")
    return PlainTextResponse(content="success")
