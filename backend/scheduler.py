"""
APScheduler configuration for periodic data scraping.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import (
    UNDERSTAT_INTERVAL, INJURIES_INTERVAL,
    FIXTURES_INTERVAL, ODDS_INTERVAL_DEFAULT,
)

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")


def _now():
    return datetime.now(timezone.utc)


def _run_async(coro):
    """Run an async coroutine from a synchronous APScheduler job."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def job_understat():
    logger.info("Scheduler: running Understat scrape")
    from scrapers.understat import scrape_all_players_sync_job
    scrape_all_players_sync_job()


def job_injuries():
    logger.info("Scheduler: running injury scrape")
    from scrapers.injuries import run_injury_scrape
    _run_async(run_injury_scrape())


def job_fixtures():
    logger.info("Scheduler: running fixtures scrape")
    from scrapers.fixtures import run_fixtures_scrape
    _run_async(run_fixtures_scrape())


def job_odds():
    logger.info("Scheduler: running odds scrape")
    from scrapers.odds import run_odds_scrape
    _run_async(run_odds_scrape())


def job_fpl_history():
    logger.info("Scheduler: running FPL match history scrape")
    from scrapers.fpl_history import run_fpl_history_scrape
    _run_async(run_fpl_history_scrape())


def start_scheduler():
    """Register all jobs and start the scheduler."""
    # Understat: first run 30 min after startup to avoid hammering on every restart.
    # Injuries + fixtures: run immediately (they're lightweight).
    _scheduler.add_job(
        job_understat,
        trigger=IntervalTrigger(seconds=UNDERSTAT_INTERVAL),
        id="understat",
        replace_existing=True,
        next_run_time=_now() + timedelta(minutes=30),
    )

    _scheduler.add_job(
        job_injuries,
        trigger=IntervalTrigger(seconds=INJURIES_INTERVAL),
        id="injuries",
        replace_existing=True,
        next_run_time=_now(),
    )

    _scheduler.add_job(
        job_fixtures,
        trigger=IntervalTrigger(seconds=FIXTURES_INTERVAL),
        id="fixtures",
        replace_existing=True,
        next_run_time=_now(),
    )

    _scheduler.add_job(
        job_odds,
        trigger=IntervalTrigger(seconds=ODDS_INTERVAL_DEFAULT),
        id="odds",
        replace_existing=True,
    )

    _scheduler.add_job(
        job_fpl_history,
        trigger=IntervalTrigger(hours=6),
        id="fpl_history",
        replace_existing=True,
        next_run_time=_now() + timedelta(minutes=5),  # 5min after startup, after injuries run
    )

    _scheduler.start()
    logger.info(
        f"Scheduler started: understat every {UNDERSTAT_INTERVAL//3600}h, "
        f"injuries every {INJURIES_INTERVAL//3600}h, "
        f"fixtures daily"
    )


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
