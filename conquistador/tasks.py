"""Celery task definitions for all agents."""

import asyncio
import logging
from celery import Celery
from celery.schedules import crontab
from conquistador.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
celery_app = Celery("conquistador", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.beat_schedule = {
    # Management agent — hourly audit
    "hourly-audit": {
        "task": "conquistador.tasks.hourly_audit",
        "schedule": crontab(minute=0),  # Every hour
    },
    # Management agent — daily summary
    "daily-summary": {
        "task": "conquistador.tasks.daily_summary",
        "schedule": crontab(hour=18, minute=0),  # 6 PM daily
    },
    # Customer service agent — send surveys
    "send-surveys": {
        "task": "conquistador.tasks.send_surveys",
        "schedule": crontab(hour=10, minute=0),  # 10 AM daily
    },
    # Revenue agent — daily report
    "daily-revenue-report": {
        "task": "conquistador.tasks.daily_revenue_report",
        "schedule": crontab(hour=18, minute=30),  # 6:30 PM daily
    },
    # Marketing agent — daily tasks
    "marketing-daily": {
        "task": "conquistador.tasks.marketing_daily",
        "schedule": crontab(hour=6, minute=0),  # 6 AM daily
    },
    # Contractor mgmt — expire stale assignments
    "expire-stale-assignments": {
        "task": "conquistador.tasks.expire_stale_assignments",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    # Contractor mgmt — reset daily counts
    "reset-daily-counts": {
        "task": "conquistador.tasks.reset_daily_counts",
        "schedule": crontab(hour=0, minute=0),  # Midnight
    },
}


def run_async(coro):
    """Helper to run async functions in Celery sync workers."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_sync_session():
    """Get a database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from conquistador.models.base import Base
    engine = create_engine(settings.database_url_sync)
    Session = sessionmaker(bind=engine)
    return Session()


def get_async_session():
    """Get an async database session for Celery tasks."""
    from conquistador.models.base import get_session_factory
    return get_session_factory()


@celery_app.task
def hourly_audit():
    async def _run():
        from conquistador.agents.management_agent import run_hourly_audit
        factory = get_async_session()
        async with factory() as db:
            await run_hourly_audit(db)
    run_async(_run())


@celery_app.task
def daily_summary():
    async def _run():
        from conquistador.agents.management_agent import send_daily_summary
        factory = get_async_session()
        async with factory() as db:
            await send_daily_summary(db)
    run_async(_run())


@celery_app.task
def send_surveys():
    async def _run():
        from conquistador.agents.customer_svc import send_pending_surveys
        factory = get_async_session()
        async with factory() as db:
            await send_pending_surveys(db)
    run_async(_run())


@celery_app.task
def daily_revenue_report():
    async def _run():
        from conquistador.agents.revenue_agent import send_daily_revenue_report
        factory = get_async_session()
        async with factory() as db:
            await send_daily_revenue_report(db)
    run_async(_run())


@celery_app.task
def marketing_daily():
    async def _run():
        from conquistador.agents.marketing_agent import run_daily_marketing_tasks
        await run_daily_marketing_tasks()
    run_async(_run())


@celery_app.task
def expire_stale_assignments():
    async def _run():
        from conquistador.agents.contractor_mgmt import expire_stale_assignments as expire
        factory = get_async_session()
        async with factory() as db:
            await expire(db)
    run_async(_run())


@celery_app.task
def reset_daily_counts():
    async def _run():
        from conquistador.agents.contractor_mgmt import reset_daily_lead_counts
        factory = get_async_session()
        async with factory() as db:
            await reset_daily_lead_counts(db)
    run_async(_run())
