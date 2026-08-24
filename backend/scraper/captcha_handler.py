"""
CAPTCHA detection and solver integration.
Supports 2Captcha and Anti-Captcha as fallback mechanisms.
"""
import asyncio
from typing import Optional, Dict
from loguru import logger
from backend.config import settings


class CaptchaHandler:
    """
    Handles CAPTCHA detection and resolution.
    Primary strategy: prevent CAPTCHAs through good fingerprinting.
    Fallback: use solver services when CAPTCHAs appear.
    """

    def __init__(self):
        self.service = settings.captcha_service
        self.api_key = settings.captcha_api_key
        self._enabled = bool(self.service and self.api_key)
        self._solve_count = 0
        self._detect_count = 0

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def update_config(self, service: str, api_key: str) -> None:
        """Update CAPTCHA solver configuration."""
        self.service = service
        self.api_key = api_key
        self._enabled = bool(service and api_key)
        logger.info(f"CAPTCHA solver {'enabled' if self._enabled else 'disabled'}: {service}")

    async def detect_captcha(self, page) -> bool:
        """
        Detect if a CAPTCHA challenge is present on the page.
        Checks for common CAPTCHA patterns from various providers.
        """
        try:
            # Check for Cloudflare Turnstile
            turnstile = await page.query_selector('iframe[src*="challenges.cloudflare.com"]')
            if turnstile:
                self._detect_count += 1
                logger.warning("Detected: Cloudflare Turnstile CAPTCHA")
                return True

            # Check for reCAPTCHA
            recaptcha = await page.query_selector('iframe[src*="recaptcha"]')
            if recaptcha:
                self._detect_count += 1
                logger.warning("Detected: Google reCAPTCHA")
                return True

            # Check for hCaptcha
            hcaptcha = await page.query_selector('iframe[src*="hcaptcha.com"]')
            if hcaptcha:
                self._detect_count += 1
                logger.warning("Detected: hCaptcha")
                return True

            # Check for generic challenge pages
            content = await page.content()
            challenge_indicators = [
                "Verify you are human",
                "Please verify",
                "checking your browser",
                "Just a moment...",
                "challenge-platform",
            ]
            for indicator in challenge_indicators:
                if indicator.lower() in content.lower():
                    self._detect_count += 1
                    logger.warning(f"Detected challenge page: '{indicator}'")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error during CAPTCHA detection: {e}")
            return False

    async def solve_captcha(self, page, captcha_type: str = "turnstile") -> bool:
        """
        Attempt to solve a detected CAPTCHA using configured service.
        Returns True if solved successfully, False otherwise.
        """
        if not self._enabled:
            logger.warning("CAPTCHA detected but no solver configured. Waiting for manual intervention...")
            # Wait and retry - sometimes CAPTCHAs resolve themselves
            await asyncio.sleep(30)
            still_captcha = await self.detect_captcha(page)
            return not still_captcha

        logger.info(f"Attempting to solve {captcha_type} CAPTCHA using {self.service}")

        try:
            if self.service == "2captcha":
                return await self._solve_2captcha(page, captcha_type)
            elif self.service == "anticaptcha":
                return await self._solve_anticaptcha(page, captcha_type)
            else:
                logger.error(f"Unknown CAPTCHA service: {self.service}")
                return False
        except Exception as e:
            logger.error(f"Failed to solve CAPTCHA: {e}")
            return False

    async def _solve_2captcha(self, page, captcha_type: str) -> bool:
        """Solve CAPTCHA using 2Captcha API."""
        import httpx

        try:
            page_url = page.url
            site_key = await self._extract_site_key(page, captcha_type)

            if not site_key:
                logger.error("Could not extract CAPTCHA site key")
                return False

            # Submit CAPTCHA to 2Captcha
            async with httpx.AsyncClient(timeout=120) as client:
                # Step 1: Submit
                submit_data = {
                    "key": self.api_key,
                    "method": "turnstile" if captcha_type == "turnstile" else "userrecaptcha",
                    "sitekey": site_key,
                    "pageurl": page_url,
                    "json": 1,
                }
                resp = await client.post("https://2captcha.com/in.php", data=submit_data)
                result = resp.json()

                if result.get("status") != 1:
                    logger.error(f"2Captcha submit failed: {result}")
                    return False

                task_id = result["request"]
                logger.info(f"2Captcha task submitted: {task_id}")

                # Step 2: Poll for result
                for _ in range(30):  # Max 150 seconds
                    await asyncio.sleep(5)
                    resp = await client.get(
                        f"https://2captcha.com/res.php?key={self.api_key}&action=get&id={task_id}&json=1"
                    )
                    result = resp.json()

                    if result.get("status") == 1:
                        token = result["request"]
                        logger.info("2Captcha solved successfully!")
                        self._solve_count += 1
                        # Inject solution
                        await self._inject_solution(page, token, captcha_type)
                        return True
                    elif result.get("request") != "CAPCHA_NOT_READY":
                        logger.error(f"2Captcha error: {result}")
                        return False

                logger.error("2Captcha timeout")
                return False

        except Exception as e:
            logger.error(f"2Captcha error: {e}")
            return False

    async def _solve_anticaptcha(self, page, captcha_type: str) -> bool:
        """Solve CAPTCHA using Anti-Captcha API."""
        import httpx

        try:
            page_url = page.url
            site_key = await self._extract_site_key(page, captcha_type)

            if not site_key:
                return False

            async with httpx.AsyncClient(timeout=120) as client:
                # Submit task
                task_data = {
                    "clientKey": self.api_key,
                    "task": {
                        "type": "TurnstileTaskProxyless" if captcha_type == "turnstile" else "RecaptchaV2TaskProxyless",
                        "websiteURL": page_url,
                        "websiteKey": site_key,
                    },
                }
                resp = await client.post("https://api.anti-captcha.com/createTask", json=task_data)
                result = resp.json()

                if result.get("errorId", 1) != 0:
                    logger.error(f"Anti-Captcha submit failed: {result}")
                    return False

                task_id = result["taskId"]

                # Poll for result
                for _ in range(30):
                    await asyncio.sleep(5)
                    resp = await client.post(
                        "https://api.anti-captcha.com/getTaskResult",
                        json={"clientKey": self.api_key, "taskId": task_id},
                    )
                    result = resp.json()

                    if result.get("status") == "ready":
                        token = result["solution"]["token"]
                        self._solve_count += 1
                        await self._inject_solution(page, token, captcha_type)
                        return True
                    elif result.get("status") != "processing":
                        logger.error(f"Anti-Captcha error: {result}")
                        return False

                return False

        except Exception as e:
            logger.error(f"Anti-Captcha error: {e}")
            return False

    async def _extract_site_key(self, page, captcha_type: str) -> Optional[str]:
        """Extract the CAPTCHA site key from the page."""
        try:
            if captcha_type == "turnstile":
                # Cloudflare Turnstile
                key = await page.evaluate("""
                    () => {
                        const el = document.querySelector('[data-sitekey]');
                        return el ? el.getAttribute('data-sitekey') : null;
                    }
                """)
                return key
            elif captcha_type == "recaptcha":
                key = await page.evaluate("""
                    () => {
                        const el = document.querySelector('.g-recaptcha[data-sitekey]');
                        return el ? el.getAttribute('data-sitekey') : null;
                    }
                """)
                return key
        except Exception:
            return None

    async def _inject_solution(self, page, token: str, captcha_type: str) -> None:
        """Inject the CAPTCHA solution token into the page."""
        try:
            if captcha_type == "turnstile":
                await page.evaluate(f"""
                    (token) => {{
                        const input = document.querySelector('[name="cf-turnstile-response"]');
                        if (input) input.value = token;
                        // Trigger callback if exists
                        if (window.turnstileCallback) window.turnstileCallback(token);
                    }}
                """, token)
            elif captcha_type == "recaptcha":
                await page.evaluate(f"""
                    (token) => {{
                        document.getElementById('g-recaptcha-response').innerHTML = token;
                        // Trigger callback
                        if (typeof ___grecaptcha_cfg !== 'undefined') {{
                            Object.keys(___grecaptcha_cfg.clients).forEach(key => {{
                                const client = ___grecaptcha_cfg.clients[key];
                                if (client && client.callback) client.callback(token);
                            }});
                        }}
                    }}
                """, token)
        except Exception as e:
            logger.error(f"Failed to inject CAPTCHA solution: {e}")

    def get_stats(self) -> Dict:
        """Get CAPTCHA handling statistics."""
        return {
            "enabled": self._enabled,
            "service": self.service or "none",
            "detected": self._detect_count,
            "solved": self._solve_count,
        }


# Singleton
captcha_handler = CaptchaHandler()
