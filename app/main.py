import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from openai import AsyncOpenAI

from app.agent import AgentCore
from app.agent.scheduler import create_scheduler
from app.cache import MemoryCache
from app.dependencies import get_settings
from app.messaging.poller import TelegramPoller
from app.messaging.telegram import TelegramClient
from app.routers import health
from app.storage.database import Database
from app.tools.registry import ToolRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings

    # Tool registry with auto-discovery
    registry = ToolRegistry()
    registry.scan_package("app.tools")
    app.state.registry = registry
    logger.info("Registered %d tools", len(registry.list_all()))

    # Cache
    cache = MemoryCache(default_ttl=settings.cache_ttl_seconds)
    app.state.cache = cache

    # LLM client
    openai_client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )
    app.state.openai_client = openai_client

    # Telegram client
    telegram_client = TelegramClient(
        bot_token=settings.telegram_bot_token
    ) if settings.telegram_bot_token else None
    app.state.telegram_client = telegram_client

    # Database
    db = Database()
    await db.connect()
    app.state.db = db

    # Agent core
    agent_core = AgentCore(
        registry=registry,
        openai_client=openai_client,
        cache=cache,
        settings=settings,
        telegram_client=telegram_client,
        db=db,
    )
    app.state.agent_core = agent_core

    # Telegram poller (long polling instead of webhook)
    poller: TelegramPoller | None = None
    if telegram_client and settings.telegram_bot_token:
        poller = TelegramPoller(
            bot_token=settings.telegram_bot_token,
            agent_core=agent_core,
            db=db,
            poll_interval=3,
        )
        await poller.start()
        app.state.poller = poller

    # Scheduler
    scheduler = create_scheduler(agent_core, settings)
    scheduler.start()
    app.state.scheduler = scheduler

    yield

    scheduler.shutdown(wait=False)
    if poller:
        await poller.stop()
    await openai_client.close()
    if telegram_client:
        await telegram_client.close()
    await db.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Agent 24/7",
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    return app


app = create_app()
