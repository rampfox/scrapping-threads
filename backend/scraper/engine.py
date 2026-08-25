"""
Main scraping engine orchestrator.
Coordinates browser, proxy, fingerprint, rate limiter, and CAPTCHA handler.
"""
import asyncio
from datetime import datetime
from typing import Optional, List, Dict
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger

from backend.scraper.stealth import apply_stealth, simulate_human_behavior
from backend.scraper.fingerprint import fingerprint_manager, FingerprintProfile
from backend.scraper.proxy_manager import proxy_manager
from backend.scraper.rate_limiter import rate_limiter
from backend.scraper.captcha_handler import captcha_handler
from backend.scraper.session_manager import session_manager
from backend.scraper.search import threads_searcher
from backend.config import settings


class ScraperEngine:
    """
    Main scraper engine that orchestrates all anti-detection components.
    """

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._is_running = False
        self._is_initialized = False
        self._scrape_count = 0
        self._error_count = 0
        self._last_error: Optional[str] = None
        self._last_scrape_at: Optional[datetime] = None
        self._logs: List[Dict] = []

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    def _add_log(self, level: str, message: str) -> None:
        """Add entry to internal log buffer."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
        }
        self._logs.append(entry)
        # Keep last 200 log entries
        if len(self._logs) > 200:
            self._logs = self._logs[-200:]

        if level == "error":
            logger.error(f"[ScraperEngine] {message}")
        elif level == "warning":
            logger.warning(f"[ScraperEngine] {message}")
        else:
            logger.info(f"[ScraperEngine] {message}")

    async def initialize(self) -> None:
        """Initialize Playwright browser."""
        if self._is_initialized:
            return

        try:
            self._add_log("info", "Initializing Playwright browser...")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            self._is_initialized = True
            self._add_log("info", "Browser initialized successfully")

            # Initialize proxy if configured
            if settings.proxy_enabled:
                proxy_list = settings.get_proxy_list()
                if proxy_list:
                    count = proxy_manager.load_from_list(proxy_list)
                    self._add_log("info", f"Loaded {count} proxies from config")
                elif settings.proxy_list_url:
                    count = await proxy_manager.load_from_url(settings.proxy_list_url)
                    self._add_log("info", f"Loaded {count} proxies from URL")
                else:
                    count = await proxy_manager.load_free_proxies()
                    self._add_log("info", f"Loaded {count} free proxies for testing")

        except Exception as e:
            self._add_log("error", f"Failed to initialize browser: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown browser and cleanup."""
        self._is_running = False
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._is_initialized = False
        self._add_log("info", "Browser shut down")

    async def _create_context(self, session_id: Optional[str] = None) -> BrowserContext:
        """
        Create a new browser context with stealth fingerprinting.
        Each context gets a unique, consistent fingerprint profile.
        """
        profile = fingerprint_manager.get_new_profile()

        # Proxy configuration
        proxy_config = proxy_manager.get_playwright_proxy(session_id) if proxy_manager.is_enabled else None

        context = await self._browser.new_context(
            viewport=profile.viewport,
            user_agent=profile.user_agent,
            locale="id-ID",
            timezone_id=profile.timezone,
            proxy=proxy_config,
            ignore_https_errors=True,
        )

        return context

    async def _create_stealth_page(self, context: BrowserContext) -> Page:
        """Create a new page with stealth scripts applied."""
        page = await context.new_page()
        await apply_stealth(page)
        return page

    async def scrape_keyword(self, keyword: str) -> List[Dict]:
        """
        Scrape Threads search results for a specific keyword.
        Full pipeline: rate limit → browser → search → parse → return.
        """
        if not self._is_initialized:
            await self.initialize()

        self._is_running = True
        posts = []
        context = None

        try:
            # Rate limiting
            await rate_limiter.acquire("threads.net")
            self._add_log("info", f"Starting scrape for keyword: '{keyword}'")

            # Create browser context with fingerprint
            session_id = f"search_{keyword}"
            context = await self._create_context(session_id)
            page = await self._create_stealth_page(context)

            # Load cookies if we have a logged-in session
            threads_user = settings.threads_username
            if threads_user:
                cookies_loaded = await session_manager.load_cookies(context, threads_user)
                if cookies_loaded:
                    self._add_log("info", f"Loaded session cookies for @{threads_user}")

            # Perform search
            posts = await threads_searcher.search_keyword(page, keyword)

            # Check for CAPTCHA
            if await captcha_handler.detect_captcha(page):
                self._add_log("warning", "CAPTCHA detected during search")
                solved = await captcha_handler.solve_captcha(page)
                if solved:
                    self._add_log("info", "CAPTCHA solved, retrying search")
                    posts = await threads_searcher.search_keyword(page, keyword)
                else:
                    self._add_log("error", "Failed to solve CAPTCHA")
                    rate_limiter.report_error("threads.net", 403)

            # Tag posts with keyword
            for post in posts:
                post["keyword"] = keyword

            # Report success
            rate_limiter.report_success("threads.net")
            proxy_info = proxy_manager.get_proxy(session_id)
            if proxy_info:
                proxy_manager.report_success(proxy_info)

            self._scrape_count += 1
            self._last_scrape_at = datetime.utcnow()
            self._add_log("info", f"Scraped {len(posts)} posts for keyword '{keyword}'")

            return posts

        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            self._add_log("error", f"Scrape failed for keyword '{keyword}': {e}")

            # Report failure for backoff
            rate_limiter.report_error("threads.net")
            return posts

        finally:
            rate_limiter.release()
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            self._is_running = False
            proxy_manager.release_session(f"search_{keyword}")

    async def login_threads(self, username: str, password: str) -> Dict:
        """
        Perform Threads login to enable search functionality.
        Returns login result status.
        """
        if not self._is_initialized:
            await self.initialize()

        context = None
        try:
            self._add_log("info", f"Attempting login for @{username}")
            context = await self._create_context()
            page = await self._create_stealth_page(context)

            success = await session_manager.login_threads(page, username, password)

            if success:
                self._add_log("info", f"Login successful for @{username}")
                return {
                    "success": True,
                    "username": username,
                    "status": "logged_in",
                    "message": "Login berhasil!",
                }
            else:
                status = session_manager.get_login_status(username)
                self._add_log("warning", f"Login failed for @{username}: {status}")
                return {
                    "success": False,
                    "username": username,
                    "status": status,
                    "message": f"Login gagal: {status}",
                }

        except Exception as e:
            self._add_log("error", f"Login error: {e}")
            return {
                "success": False,
                "username": username,
                "status": "error",
                "message": str(e),
            }
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

    def get_status(self) -> Dict:
        """Get current scraper engine status."""
        return {
            "initialized": self._is_initialized,
            "running": self._is_running,
            "scrape_count": self._scrape_count,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "last_scrape_at": self._last_scrape_at.isoformat() if self._last_scrape_at else None,
            "proxy": proxy_manager.get_stats(),
            "rate_limiter": rate_limiter.get_stats(),
            "captcha": captcha_handler.get_stats(),
            "sessions": session_manager.get_stats(),
        }

    def get_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent scraper logs."""
        return self._logs[-limit:]


# Singleton
scraper_engine = ScraperEngine()
