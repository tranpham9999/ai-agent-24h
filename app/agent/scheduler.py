import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.agent import AgentCore
from app.agent.prompts import BRIEFING_MIDDAY, BRIEFING_MORNING, BRIEFING_EVENING
from app.config import Settings

logger = logging.getLogger(__name__)


def create_scheduler(agent_core: AgentCore, settings: Settings) -> AsyncIOScheduler:
    """Create APScheduler with briefing jobs using configured hours."""

    scheduler = AsyncIOScheduler()

    platform_ctx = {"platform": "telegram", "chat_id": settings.default_telegram_chat_id}

    async def morning_job():
        logger.info("Running morning briefing")
        result = await agent_core.run(BRIEFING_MORNING, platform_context=platform_ctx)
        logger.info("Morning briefing done: %s", result[:100])

    async def midday_job():
        logger.info("Running midday check")
        result = await agent_core.run(BRIEFING_MIDDAY, platform_context=platform_ctx)
        logger.info("Midday check done: %s", result[:100])

    async def evening_job():
        logger.info("Running evening summary")
        result = await agent_core.run(BRIEFING_EVENING, platform_context=platform_ctx)
        logger.info("Evening summary done: %s", result[:100])

    scheduler.add_job(
        morning_job, "cron", hour=settings.briefing_morning_hour, minute=0, id="morning_briefing"
    )
    scheduler.add_job(
        midday_job, "cron", hour=settings.briefing_midday_hour, minute=0, id="midday_check"
    )
    scheduler.add_job(
        evening_job, "cron", hour=settings.briefing_evening_hour, minute=0, id="evening_summary"
    )

    return scheduler
