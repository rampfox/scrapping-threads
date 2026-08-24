"""
Rate limiting with random jitter, concurrency throttling,
and exponential backoff for anti-detection.
"""
import asyncio
import random
import time
from typing import Dict, Optional
from loguru import logger


class RateLimiter:
    """
    Intelligent rate limiter with:
    - Random delay (Gaussian distribution jitter)
    - Concurrency throttling per domain
    - Exponential backoff on errors (429/503)
    - Request counting per time window
    """

    def __init__(
        self,
        min_delay: float = 1.8,
        max_delay: float = 4.5,
        mean_delay: float = 3.0,
        std_delay: float = 0.8,
        max_concurrent: int = 2,
        backoff_base: float = 5.0,
        backoff_max: float = 300.0,
        backoff_factor: float = 2.0,
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.mean_delay = mean_delay
        self.std_delay = std_delay
        self.max_concurrent = max_concurrent
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.backoff_factor = backoff_factor

        # Concurrency semaphore
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Tracking
        self._last_request_time: Dict[str, float] = {}
        self._backoff_until: Dict[str, float] = {}
        self._consecutive_errors: Dict[str, int] = {}
        self._request_counts: Dict[str, list] = {}  # domain -> [timestamps]

    def _get_random_delay(self) -> float:
        """Generate random delay with Gaussian distribution."""
        delay = random.gauss(self.mean_delay, self.std_delay)
        return max(self.min_delay, min(self.max_delay, delay))

    async def acquire(self, domain: str = "threads.net") -> None:
        """
        Wait for rate limit clearance before making a request.
        Handles both delay jitter and concurrency throttling.
        """
        # Check backoff
        if domain in self._backoff_until:
            wait_until = self._backoff_until[domain]
            now = time.time()
            if now < wait_until:
                wait_time = wait_until - now
                logger.warning(f"Backoff active for {domain}, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        # Acquire semaphore for concurrency control
        await self._semaphore.acquire()

        # Apply random delay since last request
        if domain in self._last_request_time:
            elapsed = time.time() - self._last_request_time[domain]
            delay = self._get_random_delay()
            if elapsed < delay:
                wait_time = delay - elapsed
                logger.debug(f"Rate limit jitter: waiting {wait_time:.2f}s for {domain}")
                await asyncio.sleep(wait_time)

        self._last_request_time[domain] = time.time()

        # Track request count
        if domain not in self._request_counts:
            self._request_counts[domain] = []
        now = time.time()
        self._request_counts[domain].append(now)
        # Clean old entries (keep last 60 seconds)
        self._request_counts[domain] = [
            t for t in self._request_counts[domain] if now - t < 60
        ]

    def release(self) -> None:
        """Release the concurrency semaphore."""
        self._semaphore.release()

    def report_error(self, domain: str = "threads.net", status_code: int = 0) -> None:
        """
        Report an error response. Triggers exponential backoff for 429/503.
        """
        if status_code in (429, 503, 0):
            if domain not in self._consecutive_errors:
                self._consecutive_errors[domain] = 0

            self._consecutive_errors[domain] += 1
            errors = self._consecutive_errors[domain]

            # Exponential backoff: base * factor^(errors-1), capped at max
            backoff_time = min(
                self.backoff_base * (self.backoff_factor ** (errors - 1)),
                self.backoff_max,
            )

            self._backoff_until[domain] = time.time() + backoff_time
            logger.warning(
                f"Exponential backoff: {backoff_time:.1f}s for {domain} "
                f"(error #{errors}, status={status_code})"
            )

    def report_success(self, domain: str = "threads.net") -> None:
        """Report a successful response. Resets backoff counter."""
        self._consecutive_errors.pop(domain, None)
        self._backoff_until.pop(domain, None)

    def get_request_count(self, domain: str = "threads.net", window: int = 60) -> int:
        """Get number of requests made in the last `window` seconds."""
        if domain not in self._request_counts:
            return 0
        now = time.time()
        return sum(1 for t in self._request_counts[domain] if now - t < window)

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return {
            "domains": {
                domain: {
                    "requests_last_60s": self.get_request_count(domain),
                    "consecutive_errors": self._consecutive_errors.get(domain, 0),
                    "backoff_active": domain in self._backoff_until and time.time() < self._backoff_until.get(domain, 0),
                }
                for domain in self._last_request_time
            },
            "max_concurrent": self.max_concurrent,
            "delay_range": f"{self.min_delay}s - {self.max_delay}s",
        }


# Singleton
rate_limiter = RateLimiter()
