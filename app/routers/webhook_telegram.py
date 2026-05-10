import json
import logging

from fastapi import APIRouter, Request

from app.agent import AgentCore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/telegram", tags=["webhooks"])


@router.post("")
async def telegram_webhook(request: Request):
    """Receive Telegram updates, dispatch to agent, reply via bot."""
    body = await request.body()
    update = json.loads(body)

    message = update.get("message", {})
    if not message:
        return {"ok": True}

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return {"ok": True}

    # Ignore commands
    if text.startswith("/"):
        return {"ok": True}

    # Ignore bot messages
    msg_from = message.get("from", {})
    if msg_from.get("is_bot"):
        return {"ok": True}

    # Persist chat
    db = request.app.state.db
    await db.save_telegram_chat(
        chat_id=chat_id,
        title=chat.get("title") or chat.get("first_name", ""),
        username=msg_from.get("username"),
    )

    # Dispatch to agent
    agent_core: AgentCore = request.app.state.agent_core
    try:
        await agent_core.run(
            user_input=text,
            platform_context={"platform": "telegram", "chat_id": str(chat_id)},
        )
    except Exception as e:
        logger.exception("Error handling Telegram message: %s", e)

    return {"ok": True}
