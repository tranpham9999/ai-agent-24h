import hmac
import hashlib
import time

import httpx


class SlackClient:
    def __init__(self, bot_token: str) -> None:
        self._bot_token = bot_token
        self._http = httpx.AsyncClient()

    async def post_message(self, channel: str, text: str) -> dict:
        resp = await self._http.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {self._bot_token}",
                "Content-Type": "application/json",
            },
            json={"channel": channel, "text": text},
            timeout=10,
        )
        return resp.json()

    def verify_signature(self, signing_secret: str, timestamp: str, body: bytes, signature: str) -> bool:
        if abs(time.time() - float(timestamp)) > 60 * 5:
            return False
        basestring = f"v0:{timestamp}:".encode() + body
        sig = "v0=" + hmac.new(signing_secret.encode(), basestring, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, signature)

    async def close(self) -> None:
        await self._http.aclose()
