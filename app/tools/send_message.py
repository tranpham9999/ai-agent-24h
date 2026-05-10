from typing import Any

from app.messaging.telegram import TelegramClient
from app.tools.base import Tool
from app.tools.registry import ToolRegistry
from app.config import Settings


async def _send_message(
    message: str,
    channels: list[str] | None = None,
    telegram_chat_id: str | None = None,
    _telegram_client: TelegramClient | None = None,
    _settings: Settings | None = None,
    **kwargs: Any,
) -> dict:
    """Send a message via Telegram using shared client."""
    if not channels:
        channels = ["telegram"]

    results: dict = {}

    for channel in channels:
        c = channel.lower().strip()
        if c == "telegram" and _telegram_client:
            target = telegram_chat_id or (_settings.default_telegram_chat_id if _settings else "")
            if not target:
                results["telegram"] = {"error": "No telegram_chat_id provided or configured"}
                continue
            try:
                resp_data = await _telegram_client.send_message(target, message)
                results["telegram"] = {"ok": resp_data.get("ok", False)}
            except Exception as e:
                results["telegram"] = {"error": str(e)}

    return {"success": True, "data": results}


def register(registry: ToolRegistry) -> None:
    registry.register(
        Tool(
            name="send_message",
            description="Send a message via Telegram",
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message content to send",
                    },
                    "channels": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["telegram"]},
                        "description": "Platforms to send to (default: telegram)",
                    },
                    "telegram_chat_id": {
                        "type": "string",
                        "description": "Telegram chat ID (auto-injected by runtime)",
                    },
                },
                "required": ["message"],
            },
            handler=_send_message,
            cache_ttl=None,
        )
    )
