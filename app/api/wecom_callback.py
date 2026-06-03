from fastapi import APIRouter, Request, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse
import xml.etree.ElementTree as ET
from app.channels.wecom_app import WeComAppClient
from app.handlers.message_handler import MessageHandler

router = APIRouter(prefix="/wecom", tags=["wecom"])
wecom_client = WeComAppClient()
message_handler = MessageHandler()


@router.get("/callback", response_class=PlainTextResponse)
async def verify_url(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    result = wecom_client.verify_url(msg_signature, timestamp, nonce, echostr)
    if result:
        return PlainTextResponse(content=result)
    return PlainTextResponse(content="fail", status_code=403)


@router.post("/callback", response_class=PlainTextResponse)
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
):
    body = await request.body()
    root = ET.fromstring(body)
    encrypt = root.findtext("Encrypt", "")
    msg_data = wecom_client.decrypt_message(msg_signature, timestamp, nonce, encrypt)
    if msg_data:
        background_tasks.add_task(message_handler.handle_wecom_message, msg_data)
    return PlainTextResponse(content="success")
