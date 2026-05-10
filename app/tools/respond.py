from app.tools.base import Tool
from app.tools.registry import ToolRegistry


async def _respond(message: str) -> dict:
    """Reply to the user when no other tool is needed."""
    return {"success": True, "data": {"message": message}}


def register(registry: ToolRegistry) -> None:
    registry.register(
        Tool(
            name="respond",
            description="Reply directly to the user when no other tool is needed (e.g. greetings, chit-chat, clarification, or any response that does not require fetching external data)",
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The text response to return to the user",
                    }
                },
                "required": ["message"],
            },
            handler=_respond,
            cache_ttl=None,
        )
    )
