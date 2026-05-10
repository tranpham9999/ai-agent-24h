import httpx


class TelegramClient:
    def __init__(self, bot_token: str) -> None:
        self._base_url = f"https://api.telegram.org/bot{bot_token}"
        self._http = httpx.AsyncClient()

    async def set_webhook(self, url: str) -> dict:
        resp = await self._http.post(
            f"{self._base_url}/setWebhook",
            json={"url": url},
            timeout=10,
        )
        return resp.json()

    async def send_message(self, chat_id: str, text: str) -> dict:
        resp = await self._http.post(
            f"{self._base_url}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        return resp.json()

    async def close(self) -> None:
        await self._http.aclose()
