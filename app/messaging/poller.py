import asyncio
import logging

import httpx

from app.agent import AgentCore

logger = logging.getLogger(__name__)


class TelegramPoller:
    """Poll Telegram for new messages using getUpdates (long polling).

    No webhook / public URL needed — works on localhost.
    """

    def __init__(self, bot_token: str, agent_core: AgentCore, db: object, poll_interval: int = 30) -> None:
        self._base_url = f"https://api.telegram.org/bot{bot_token}"
        self._http = httpx.AsyncClient()
        self._agent = agent_core
        self._db = db
        self._poll_interval = poll_interval
        self._last_update_id: int = 0
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        # Delete any existing webhook so getUpdates works
        try:
            resp = await self._http.post(f"{self._base_url}/deleteWebhook", timeout=10)
            data = resp.json()
            logger.info("Telegram deleteWebhook: %s", data)
        except Exception as e:
            logger.warning("Failed to delete Telegram webhook: %s", e)

        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Telegram poller started (interval=%ds)", self._poll_interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._http.aclose()
        logger.info("Telegram poller stopped")

    async def _poll_loop(self) -> None:
        while True:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Telegram poll error: %s", e)
            await asyncio.sleep(self._poll_interval)

    async def _poll_once(self) -> None:
        resp = await self._http.post(
            f"{self._base_url}/getUpdates",
            json={
                "offset": self._last_update_id + 1,
                "timeout": 10,
                "allowed_updates": ["message"],
            },
            timeout=15,
        )
        data = resp.json()
        if not data.get("ok"):
            return

        for update in data.get("result", []):
            self._last_update_id = update["update_id"]
            await self._handle_update(update)

    async def _handle_update(self, update: dict) -> None:
        message = update.get("message", {})
        if not message:
            return

        chat = message.get("chat", {})
        chat_id = chat.get("id")
        text = message.get("text", "").strip()

        if not chat_id or not text:
            return
        if text.startswith("/"):
            return
        if message.get("from", {}).get("is_bot"):
            return

        # Persist chat
        await self._db.save_telegram_chat(
            chat_id=chat_id,
            title=chat.get("title") or chat.get("first_name", ""),
            username=message.get("from", {}).get("username"),
        )

        # Dispatch to agent — agent will call send_message tool which replies via Telegram
        try:
            await self._agent.run(
                user_input=text,
                platform_context={"platform": "telegram", "chat_id": str(chat_id)},
            )
        except Exception as e:
            logger.exception("Error handling Telegram message: %s", e)
