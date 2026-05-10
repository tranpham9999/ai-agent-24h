import json
import logging

from fastapi import APIRouter, Request

from app.agent import AgentCore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/slack", tags=["webhooks"])


@router.post("")
async def slack_webhook(request: Request):
    """Receive Slack events (slash commands, messages)."""
    body = await request.body()
    headers = request.headers

    # Parse payload
    content_type = headers.get("content-type", "")
    if "application/json" not in content_type:
        return {"ok": False, "error": "unsupported content type"}

    payload = json.loads(body)

    # Slack URL verification challenge
    if "challenge" in payload:
        return {"challenge": payload["challenge"]}

    # Only process event callbacks
    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        event_type = event.get("type", "")

        # Ignore bot messages to prevent echo loops
        if event.get("subtype") == "bot_message" or event.get("bot_id"):
            return {"ok": True}

        # Verify signature (log warning on failure, still ack to avoid retries)
        settings = request.app.state.settings
        slack_client = request.app.state.slack_client
        if slack_client and settings.slack_signing_secret:
            timestamp = headers.get("x-slack-request-timestamp", "")
            signature = headers.get("x-slack-signature", "")
            if not slack_client.verify_signature(settings.slack_signing_secret, timestamp, body, signature):
                logger.warning("Slack signature verification failed")

        # Handle message events
        if event_type == "message":
            text = event.get("text", "").strip()
            channel = event.get("channel", "")
            if text and channel:
                import asyncio

                asyncio.create_task(
                    _handle_slack_message(
                        request.app.state.agent_core,
                        text,
                        channel,
                    )
                )

    # Always ack immediately (Slack 3-second constraint)
    return {"ok": True}


async def _handle_slack_message(agent_core: AgentCore, text: str, channel: str) -> None:
    """Process a Slack message in the background."""
    try:
        await agent_core.run(
            user_input=text,
            platform_context={"platform": "slack", "channel_id": channel},
        )
    except Exception as e:
        logger.exception("Error handling Slack message: %s", e)
