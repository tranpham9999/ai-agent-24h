import asyncio

from ddgs import DDGS

from app.tools.base import Tool
from app.tools.registry import ToolRegistry


async def _web_search(query: str, limit: int = 5) -> dict:
    """Search the web using DuckDuckGo (free, no API key)."""
    try:
        results = await asyncio.to_thread(_search_sync, query, limit)
        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _search_sync(query: str, limit: int) -> list[dict]:
    """Synchronous DuckDuckGo search (runs in thread pool)."""
    with DDGS() as ddgs:
        entries = []
        for i, r in enumerate(ddgs.text(query, max_results=limit)):
            entries.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
            )
            if i + 1 >= limit:
                break
        return entries


def register(registry: ToolRegistry) -> None:
    registry.register(
        Tool(
            name="web_search",
            description="Search the web for current information (free, no API key needed)",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (max 10)",
                    },
                },
                "required": ["query"],
            },
            handler=_web_search,
            cache_ttl=600,
        )
    )
