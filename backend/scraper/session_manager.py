"""
Threads account session management.
Handles login, cookie persistence, and session health checking.
"""
import json
import asyncio
import random
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

    # Threads login dapat redirect ke Instagram atau tetap di Threads
    LOGIN_URLS = [
        "https://www.threads.net/login",
        "https://www.threads.net/",
    ]

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._cookies: Dict[str, list] = {}   # username -> cookies
        self._login_status: Dict[str, str] = {}
        self._login_errors: Dict[str, str] = {}  # username -> detail error
        self._init_encryption()

    def _init_encryption(self) -> None:
        """Initialize Fernet encryption with secret key."""
        try:
            key = settings.get_secret_key()
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
        Threads menggunakan sistem auth Instagram.
        """
        from backend.scraper.stealth import simulate_human_behavior

        try:
            logger.info(f"[Login] Memulai login untuk @{username}")

            # Step 1: Navigasi ke halaman login Threads
            logger.info("[Login] Step 1: Navigasi ke threads.net/login...")
            await page.goto(
                "https://www.threads.net/login",
                wait_until="domcontentloaded",
                timeout=30000
            )
            await asyncio.sleep(3)

            current_url = page.url
            logger.info(f"[Login] URL setelah navigasi: {current_url}")

            # Step 2: Cek apakah sudah login
            if await self._check_logged_in(page):
                logger.info(f"[Login] Sudah login sebagai @{username}")
                await self._save_cookies(page, username)
                self._login_status[username] = "logged_in"
                return True

            # Step 3: Deteksi form login yang aktif
            logger.info("[Login] Step 3: Mencari form login...")
            form_type = await self._detect_login_form(page)
            logger.info(f"[Login] Form ditemukan: {form_type}")

            if form_type == "not_found":
                # Coba screenshot untuk debug
                page_title = await page.title()
                logger.error(f"[Login] Form tidak ditemukan! Judul halaman: '{page_title}', URL: {page.url}")
                page_text = await page.evaluate("() => document.body.innerText.substring(0, 500)")
                logger.error(f"[Login] Konten halaman: {page_text[:300]}")
                self._login_status[username] = "error"
                self._login_errors[username] = f"Form login tidak ditemukan. URL: {page.url}, Judul: {page_title}"
                return False

            # Step 4: Isi username
            logger.info("[Login] Step 4: Mengisi username...")
            username_filled = await self._fill_username(page, username)
            if not username_filled:
                logger.error("[Login] Gagal mengisi field username")
                self._login_errors[username] = "Gagal mengisi field username - selector tidak ditemukan"
                self._login_status[username] = "error"
                return False

            await asyncio.sleep(random.uniform(0.8, 1.5))

            # Step 5: Isi password
            logger.info("[Login] Step 5: Mengisi password...")
            password_filled = await self._fill_password(page, password)
            if not password_filled:
                logger.error("[Login] Gagal mengisi field password")
                self._login_errors[username] = "Gagal mengisi field password - selector tidak ditemukan"
                self._login_status[username] = "error"
                return False

            await asyncio.sleep(random.uniform(0.5, 1.0))

            # Step 6: Klik tombol login
            logger.info("[Login] Step 6: Mengklik tombol login...")
            btn_clicked = await self._click_login_button(page)
            if not btn_clicked:
                logger.error("[Login] Tombol login tidak ditemukan")
                self._login_errors[username] = "Tombol login tidak ditemukan di halaman"
                self._login_status[username] = "error"
                return False

            # Step 7: Tunggu navigasi setelah login
            logger.info("[Login] Step 7: Menunggu respons server...")
            await asyncio.sleep(6)

            post_login_url = page.url
            logger.info(f"[Login] URL setelah klik login: {post_login_url}")

            # Step 8: Cek berbagai kemungkinan kondisi
            page_content = await page.content()
            page_lower = page_content.lower()

            # 2FA / verification
            if any(kw in page_lower for kw in ["two_factor", "verification", "security_code", "verifikasi", "kode keamanan"]):
                logger.warning("[Login] 2FA/verifikasi diperlukan!")
                self._login_status[username] = "2fa_required"
                self._login_errors[username] = "Login memerlukan verifikasi 2FA. Silakan nonaktifkan 2FA sementara."
                return False

            # Error password salah / akun tidak ditemukan
            if any(kw in page_lower for kw in [
                "your password was incorrect", "password yang anda masukkan tidak benar",
                "sorry, your password was incorrect",
                "find your account", "we couldn't find your account",
            ]):
                logger.error("[Login] Password salah atau akun tidak ditemukan")
                self._login_status[username] = "wrong_credentials"
                self._login_errors[username] = "Password salah atau username tidak ditemukan"
                return False

            # Akun terkunci / suspended
            if any(kw in page_lower for kw in ["account suspended", "temporarily locked", "we've locked"]):
                logger.error("[Login] Akun dikunci/suspended")
                self._login_status[username] = "account_locked"
                self._login_errors[username] = "Akun dikunci sementara oleh Instagram. Coba lagi nanti."
                return False

            # Checkpoint (suspicious activity)
            if any(kw in page_lower for kw in ["checkpoint", "unusual", "confirm your information"]):
                logger.warning("[Login] Checkpoint terdeteksi - aktivitas mencurigakan")
                self._login_status[username] = "checkpoint"
                self._login_errors[username] = "Checkpoint Instagram terdeteksi. Perlu konfirmasi manual di browser."
                return False

            # Step 9: Verifikasi login berhasil
            if await self._check_logged_in(page):
                logger.info(f"[Login] ✅ Login berhasil untuk @{username}")
                await self._save_cookies(page, username)
                self._login_status[username] = "logged_in"
                self._login_errors.pop(username, None)
                return True
            else:
                # Log detail untuk debug
                page_title = await page.title()
                logger.error(f"[Login] ❌ Login gagal. URL: {post_login_url}, Judul: {page_title}")
                logger.error(f"[Login] Konten awal: {page_content[:400]}")
                self._login_status[username] = "failed"
                self._login_errors[username] = (
                    f"Login tidak berhasil. "
                    f"URL akhir: {post_login_url} | "
                    f"Judul: {page_title}"
                )
                return False

        except asyncio.TimeoutError:
            msg = "Timeout saat membuka halaman login Threads (>30 detik)"
            logger.error(f"[Login] {msg}")
            self._login_status[username] = "timeout"
            self._login_errors[username] = msg
            return False
        except Exception as e:
            msg = f"Exception: {type(e).__name__}: {e}"
            logger.error(f"[Login] Error: {msg}")
            self._login_status[username] = "error"
            self._login_errors[username] = msg
            return False

    async def _detect_login_form(self, page) -> str:
        """Deteksi jenis form login yang ada di halaman."""
        # Cek apakah redirect ke Instagram
        current_url = page.url
        if "instagram.com" in current_url:
            return "instagram"

        # Cek form Threads/Meta
        try:
            # Coba tunggu input muncul (Threads mungkin lazy-load form)
            await page.wait_for_selector(
                'input[name="username"], input[name="email"], '
                'input[aria-label*="sername"], input[aria-label*="mail"], '
                'input[type="text"], input[type="email"]',
                timeout=8000
            )
            return "threads"
        except Exception:
            pass

        # Cek teks halaman untuk clue
        try:
            body_text = await page.evaluate("() => document.body.innerText.toLowerCase()")
            if "log in" in body_text or "masuk" in body_text or "sign in" in body_text:
                return "unknown_with_text"
        except Exception:
            pass

        return "not_found"

    async def _fill_username(self, page, username: str) -> bool:
        """Isi field username/email dengan berbagai selector fallback."""
        selectors = [
            'input[name="username"]',
            'input[name="email"]',
            'input[aria-label="Username"]',
            'input[aria-label="Phone number, username, or email"]',
            'input[aria-label="Nomor telepon, nama pengguna, atau email"]',
            'input[autocomplete="username"]',
            'input[type="text"]:visible',
            'input[type="email"]:visible',
        ]

        for selector in selectors:
            try:
                el = await page.wait_for_selector(selector, timeout=3000, state="visible")
                if el:
                    await el.click()
                    await asyncio.sleep(0.3)
                    await el.fill("")
                    await el.type(username, delay=random.randint(60, 130))
                    logger.info(f"[Login] Username diisi via selector: {selector}")
                    return True
            except Exception:
                continue

        return False

    async def _fill_password(self, page, password: str) -> bool:
        """Isi field password dengan berbagai selector fallback."""
        selectors = [
            'input[name="password"]',
            'input[type="password"]',
            'input[aria-label="Password"]',
            'input[aria-label="Kata sandi"]',
            'input[autocomplete="current-password"]',
        ]

        for selector in selectors:
            try:
                el = await page.wait_for_selector(selector, timeout=3000, state="visible")
                if el:
                    await el.click()
                    await asyncio.sleep(0.3)
                    await el.fill("")
                    await el.type(password, delay=random.randint(60, 130))
                    logger.info(f"[Login] Password diisi via selector: {selector}")
                    return True
            except Exception:
                continue

        return False

    async def _click_login_button(self, page) -> bool:
        """Klik tombol login dengan berbagai selector fallback."""
        selectors = [
            'button[type="submit"]',
            'div[role="button"]:text-matches("Log in|Masuk|Sign in", "i")',
            'button:text-matches("Log in|Masuk|Sign in", "i")',
            '[data-testid="royal_login_button"]',
            'button[class*="login"]',
        ]

        for selector in selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    is_visible = await el.is_visible()
                    is_enabled = await el.is_enabled()
                    if is_visible and is_enabled:
                        await el.click()
                        logger.info(f"[Login] Tombol diklik via selector: {selector}")
                        return True
            except Exception:
                continue

        # Fallback: tekan Enter di field password
        try:
            pw_el = await page.query_selector('input[type="password"]')
            if pw_el:
                await pw_el.press("Enter")
                logger.info("[Login] Fallback: tekan Enter di password field")
                return True
        except Exception:
            pass

        return False

    async def _check_logged_in(self, page) -> bool:
        """Cek apakah sudah login ke Threads."""
        try:
            url = page.url
            # Jika masih di halaman login, belum login
            if any(kw in url for kw in ["/login", "/accounts/login", "accounts/signup"]):
                return False

            # Cek apakah ada elemen yang hanya muncul saat login
            logged_in_indicators = [
                '[aria-label="Home"]',
                'a[href="/"]',
                '[data-pressable-container]',
                'div[role="main"]',
                'a[href*="/activity"]',
                'nav',
            ]

            for selector in logged_in_indicators:
                try:
                    el = await page.wait_for_selector(selector, timeout=2000)
                    if el:
                        return True
                except Exception:
                    continue

            # Cek via URL — kalau sudah di threads.net tanpa /login = logged in
            if "threads.net" in url and "/login" not in url:
                # Pastikan bukan halaman error
                title = await page.title()
                if title and "threads" in title.lower():
                    return True

            return False
        except Exception:
            return False

    async def _save_cookies(self, page, username: str) -> None:
        """Save browser cookies untuk session persistence."""
        try:
            context = page.context
            cookies = await context.cookies()
            self._cookies[username] = cookies
            logger.info(f"[Login] Saved {len(cookies)} cookies untuk @{username}")
        except Exception as e:
            logger.error(f"Gagal menyimpan cookies: {e}")

    async def load_cookies(self, context, username: str) -> bool:
        """Load saved cookies ke browser context."""
        try:
            if username in self._cookies:
                cookies = self._cookies[username]
                await context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies untuk @{username}")
                return True
            return False
        except Exception as e:
            logger.error(f"Gagal load cookies: {e}")
            return False

    def get_cookies_json(self, username: str) -> Optional[str]:
        """Get encrypted cookies JSON untuk disimpan ke database."""
        if username in self._cookies:
            return self.encrypt_data(json.dumps(self._cookies[username]))
        return None

    def set_cookies_from_json(self, username: str, encrypted_json: str) -> None:
        """Restore cookies dari encrypted JSON (dari database)."""
        try:
            decrypted = self.decrypt_data(encrypted_json)
            if decrypted:
                self._cookies[username] = json.loads(decrypted)
        except Exception as e:
            logger.error(f"Gagal restore cookies: {e}")

    def get_login_status(self, username: str) -> str:
        return self._login_status.get(username, "not_logged_in")

    def get_login_error(self, username: str) -> str:
        """Ambil pesan error detail terakhir untuk username ini."""
        return self._login_errors.get(username, "")

    def get_stats(self) -> Dict:
        all_users = set(list(self._login_status.keys()) + list(self._cookies.keys()))
        return {
            "accounts": {
                u: {
                    "status": self._login_status.get(u, "not_logged_in"),
                    "has_cookies": u in self._cookies,
                    "error": self._login_errors.get(u, ""),
                }
                for u in all_users
            }
        }


# Singleton
session_manager = SessionManager()
