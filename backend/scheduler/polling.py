"""
APScheduler-based polling for periodic Threads scraping.
Manages scraping jobs for active keywords.
"""
import asyncio
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update
from loguru import logger

from backend.config import settings
from backend.database import async_session
from backend.models import Keyword, ThreadPost, ScraperSetting
from backend.scraper.engine import scraper_engine


class PollingScheduler:
    """
    Manages periodic scraping jobs using APScheduler.
    Each active keyword gets its own polling job.
    """

    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._is_running = False
        self._interval = settings.polling_interval
        self._job_id = "threads_scraping_job"

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def interval(self) -> int:
        return self._interval

    async def start(self) -> None:
        """Start the polling scheduler."""
        if self._is_running:
            logger.warning("Scheduler already running")
            return

        try:
            # Load interval from DB settings
            await self._load_interval()

            # Add the main polling job
            self._scheduler.add_job(
                self._scrape_all_keywords,
                trigger=IntervalTrigger(seconds=self._interval),
                id=self._job_id,
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=60,
            )

            self._scheduler.start()
            self._is_running = True
            logger.info(f"Scheduler started with interval: {self._interval}s")

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")

    async def stop(self) -> None:
        """Stop the polling scheduler."""
        if not self._is_running:
            return

        try:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")

    async def update_interval(self, seconds: int) -> None:
        """Update the polling interval."""
        # Validate range: 30s to 600s (10 min)
        seconds = max(30, min(600, seconds))
        self._interval = seconds

        # Save to DB
        await self._save_interval(seconds)

        # Reschedule if running
        if self._is_running:
            self._scheduler.reschedule_job(
                self._job_id,
                trigger=IntervalTrigger(seconds=seconds),
            )
            logger.info(f"Polling interval updated to {seconds}s")

    async def _load_interval(self) -> None:
        """Load polling interval from database."""
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(ScraperSetting).where(ScraperSetting.key == "polling_interval")
                )
                setting = result.scalar_one_or_none()
                if setting and setting.value:
                    self._interval = int(setting.value)
        except Exception:
            pass  # Use default

    async def _save_interval(self, seconds: int) -> None:
        """Save polling interval to database."""
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(ScraperSetting).where(ScraperSetting.key == "polling_interval")
                )
                setting = result.scalar_one_or_none()
                if setting:
                    setting.value = str(seconds)
                    setting.updated_at = datetime.utcnow()
                else:
                    setting = ScraperSetting(
                        key="polling_interval",
                        value=str(seconds),
                    )
                    session.add(setting)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to save interval: {e}")

    async def _scrape_all_keywords(self) -> None:
        """
        Main polling job: scrape all active keywords.
        Called periodically by the scheduler.
        """
        try:
            logger.info("Starting scheduled scrape cycle...")

            # Get all active keywords
            async with async_session() as session:
                result = await session.execute(
                    select(Keyword).where(Keyword.is_active == True)
                )
                keywords = result.scalars().all()

            if not keywords:
                logger.info("No active keywords to scrape")
                return

            logger.info(f"Scraping {len(keywords)} active keywords")

            for kw in keywords:
                try:
                    # Scrape this keyword
                    posts = await scraper_engine.scrape_keyword(kw.keyword)

                    # Save results to database
                    saved_count = await self._save_posts(posts, kw.keyword)

                    # Update keyword stats
                    async with async_session() as session:
                        result = await session.execute(
                            select(Keyword).where(Keyword.id == kw.id)
                        )
                        db_kw = result.scalar_one_or_none()
                        if db_kw:
                            db_kw.last_scraped_at = datetime.utcnow()
                            db_kw.post_count = (db_kw.post_count or 0) + saved_count
                            await session.commit()

                    logger.info(f"Keyword '{kw.keyword}': saved {saved_count} new posts")

                except Exception as e:
                    logger.error(f"Error scraping keyword '{kw.keyword}': {e}")

        except Exception as e:
            logger.error(f"Scheduled scrape cycle error: {e}")

    async def _save_posts(self, posts: list, keyword: str) -> int:
        """Save scraped posts to database, skipping duplicates."""
        saved = 0

        async with async_session() as session:
            for post_data in posts:
                try:
                    thread_id = post_data.get("thread_id")
                    if not thread_id:
                        continue

                    # Check if already exists
                    existing = await session.execute(
                        select(ThreadPost).where(ThreadPost.thread_id == thread_id)
                    )
                    if existing.scalar_one_or_none():
                        continue

                    # Create new post
                    post = ThreadPost(
                        thread_id=thread_id,
                        code=post_data.get("code"),
                        username=post_data.get("username", ""),
                        display_name=post_data.get("display_name"),
                        user_pic=post_data.get("user_pic"),
                        is_verified=post_data.get("is_verified", False),
                        content=post_data.get("content"),
                        posted_at=post_data.get("posted_at"),
                        keyword=keyword,
                        url=post_data.get("url"),
                        like_count=post_data.get("like_count", 0),
                        reply_count=post_data.get("reply_count", 0),
                        images=post_data.get("images"),
                        videos=post_data.get("videos"),
                        raw_data=post_data,
                    )
                    session.add(post)
                    saved += 1

                except Exception as e:
                    logger.error(f"Error saving post: {e}")

            if saved > 0:
                await session.commit()

        return saved

    async def trigger_keyword_scrape(self, keyword: str) -> int:
        """Manually trigger a scrape for a specific keyword."""
        posts = await scraper_engine.scrape_keyword(keyword)
        saved = await self._save_posts(posts, keyword)
        return saved

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self._is_running,
            "interval": self._interval,
            "next_run": None,
        }


# Singleton
polling_scheduler = PollingScheduler()
