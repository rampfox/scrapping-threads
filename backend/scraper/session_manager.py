"""
Threads account session management.
Handles login, cookie persistence, and session health checking.
"""
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from cryptography.fernet import Fernet
from loguru import logger
from backend.config import settings


class SessionManager:
    """
    Manages Threads login sessions and cookies.
    Cookies are encrypted before storage for security.
    """

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._cookies: Dict[str, list] = {}  # username -> cookies
        self._login_status: Dict[str, str] = {}
        self._init_encryption()

    def _init_encryption(self) -> None:
        """Initialize Fernet encryption with secret key."""
        try:
            key = settings.get_secret_key()
            # Fernet requires 32 url-safe base64 bytes
            import base64
            import hashlib
            key_bytes = hashlib.sha256(key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            self._fernet = Fernet(fernet_key)
        except Exception as e:
            logger.error(f"Failed to init encryption: {e}")
            self._fernet = None

    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data (passwords, cookies)."""
        if not self._fernet:
            logger.warning("Encryption not available, storing as plain text")
            return data
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted: str) -> str:
        """Decrypt encrypted data."""
        if not self._fernet:
            return encrypted
        try:
            return self._fernet.decrypt(encrypted.encode()).decode()
        except Exception:
            logger.error("Failed to decrypt data - key may have changed")
            return ""

    async def login_threads(self, page, username: str, password: str) -> bool:
        """
        Perform Threads login using Playwright browser.
        Navigates to Instagram login (Threads uses Instagram auth).
        """
        from backend.scraper.stealth import simulate_human_behavior

        try:
            logger.info(f"Attempting Threads login for @{username}")

            # Navigate to Threads login (redirects to Instagram)
            await page.goto("https://www.threads.net/login", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # Check if already logged in
            if await self._check_logged_in(page):
                logger.info(f"Already logged in as @{username}")
                await self._save_cookies(page, username)
                return True

            # Simulate human behavior before typing
            await simulate_human_behavior(page, duration=1.5)

            # Find and fill login form
            # Threads uses Instagram's login system
            username_input = await page.wait_for_selector(
                'input[name="username"], input[aria-label="Username"], input[type="text"]',
                timeout=10000
            )
            if username_input:
                await username_input.click()
                await asyncio.sleep(0.3)
                await username_input.fill("")
                # Type slowly like a human
                for char in username:
                    await username_input.type(char, delay=50 + __import__('random').randint(0, 100))
                await asyncio.sleep(0.5)

            password_input = await page.wait_for_selector(
                'input[name="password"], input[aria-label="Password"], input[type="password"]',
                timeout=5000
            )
            if password_input:
                await password_input.click()
                await asyncio.sleep(0.3)
                for char in password:
                    await password_input.type(char, delay=50 + __import__('random').randint(0, 100))
                await asyncio.sleep(0.5)

            # Click login button
            login_btn = await page.query_selector(
                'button[type="submit"], div[role="button"]:has-text("Log in"), '
                'button:has-text("Log in"), button:has-text("Masuk")'
            )
            if login_btn:
                await asyncio.sleep(0.5)
                await login_btn.click()

            # Wait for navigation after login
            await asyncio.sleep(5)

            # Check for 2FA or challenge
            page_content = await page.content()
            if "two_factor" in page_content.lower() or "verification" in page_content.lower():
                logger.warning("2FA/verification required - login incomplete")
                self._login_status[username] = "2fa_required"
                return False

            # Verify login success
            if await self._check_logged_in(page):
                logger.info(f"Login successful for @{username}")
                await self._save_cookies(page, username)
                self._login_status[username] = "logged_in"
                return True
            else:
                logger.error(f"Login failed for @{username}")
                self._login_status[username] = "failed"
                return False

        except Exception as e:
            logger.error(f"Login error for @{username}: {e}")
            self._login_status[username] = "error"
            return False

    async def _check_logged_in(self, page) -> bool:
        """Check if currently logged into Threads."""
        try:
            # Check for logged-in indicators
            url = page.url
            if "login" in url.lower():
                return False

            # Check for user-specific elements
            user_el = await page.query_selector(
                '[data-pressable-container="true"], '
                'a[href*="/activity"], '
                'div[role="navigation"]'
            )
            return user_el is not None
        except Exception:
            return False

    async def _save_cookies(self, page, username: str) -> None:
        """Save browser cookies for session persistence."""
        try:
            context = page.context
            cookies = await context.cookies()
            cookies_json = json.dumps(cookies)
            encrypted = self.encrypt_data(cookies_json)
            self._cookies[username] = cookies
            logger.info(f"Saved {len(cookies)} cookies for @{username}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    async def load_cookies(self, context, username: str) -> bool:
        """Load saved cookies into a browser context."""
        try:
            if username in self._cookies:
                cookies = self._cookies[username]
                await context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies for @{username}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False

    def get_cookies_json(self, username: str) -> Optional[str]:
        """Get encrypted cookies JSON for database storage."""
        if username in self._cookies:
            return self.encrypt_data(json.dumps(self._cookies[username]))
        return None

    def set_cookies_from_json(self, username: str, encrypted_json: str) -> None:
        """Restore cookies from encrypted JSON (from database)."""
        try:
            decrypted = self.decrypt_data(encrypted_json)
            if decrypted:
                self._cookies[username] = json.loads(decrypted)
        except Exception as e:
            logger.error(f"Failed to restore cookies: {e}")

    def get_login_status(self, username: str) -> str:
        """Get the login status for a username."""
        return self._login_status.get(username, "not_logged_in")

    def get_stats(self) -> Dict:
        return {
            "accounts": {
                username: {
                    "status": self._login_status.get(username, "not_logged_in"),
                    "has_cookies": username in self._cookies,
                }
                for username in set(list(self._login_status.keys()) + list(self._cookies.keys()))
            }
        }


# Singleton
session_manager = SessionManager()
