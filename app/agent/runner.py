"""CLI runner for ad-hoc agent queries."""

import argparse
import asyncio
import os

from openai import AsyncOpenAI

from app.agent import AgentCore
from app.cache import MemoryCache
from app.config import Settings
from app.tools.registry import ToolRegistry


async def main() -> None:
    parser = argparse.ArgumentParser(description="AI Agent 24/7 CLI")
    parser.add_argument("--input", "-i", required=True, help="User input for the agent")
    parser.add_argument("--timezone", default="Asia/Ho_Chi_Minh", help="Timezone")
    args = parser.parse_args()

    settings = Settings()

    registry = ToolRegistry()
    registry.scan_package("app.tools")

    openai_client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )
    cache = MemoryCache()

    agent = AgentCore(
        registry=registry,
        openai_client=openai_client,
        cache=cache,
        settings=settings,
    )

    result = await agent.run(user_input=args.input, timezone=args.timezone)
    print(result)

    await openai_client.close()


if __name__ == "__main__":
    asyncio.run(main())
