"""
HTTP fingerprint management: User-Agent rotation, header construction,
and TLS fingerprint consistency.
"""
import random
from typing import Dict, Optional, Tuple
from loguru import logger


# Realistic modern browser User-Agents (Chrome, Firefox, Edge on Windows/Mac/Linux)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
]

# Platform-consistent mappings (UA <-> platform <-> OS)
PLATFORM_MAP = {
    "Windows": {
        "platform": "Win32",
        "oscpu": "Windows NT 10.0; Win64; x64",
        "sec_ch_ua_platform": '"Windows"',
    },
    "Macintosh": {
        "platform": "MacIntel",
        "oscpu": "Intel Mac OS X 10.15",
        "sec_ch_ua_platform": '"macOS"',
    },
    "Linux": {
        "platform": "Linux x86_64",
        "oscpu": "Linux x86_64",
        "sec_ch_ua_platform": '"Linux"',
    },
}

# Accept-Language variations
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9,id;q=0.8",
    "en-US,en;q=0.9",
    "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "en-US,en;q=0.9,id-ID;q=0.8,id;q=0.7",
]


class FingerprintProfile:
    """A consistent browser fingerprint profile for a single session."""

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or random.choice(USER_AGENTS)
        self.accept_language = random.choice(ACCEPT_LANGUAGES)
        self.platform_info = self._detect_platform()
        self.viewport = self._random_viewport()
        self.timezone = "Asia/Jakarta"

    def _detect_platform(self) -> Dict:
        """Detect platform from User-Agent string."""
        ua = self.user_agent
        if "Windows" in ua:
            return PLATFORM_MAP["Windows"]
        elif "Macintosh" in ua:
            return PLATFORM_MAP["Macintosh"]
        elif "Linux" in ua:
            return PLATFORM_MAP["Linux"]
        return PLATFORM_MAP["Windows"]  # Default

    def _random_viewport(self) -> Dict[str, int]:
        """Generate a common screen resolution."""
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1680, "height": 1050},
            {"width": 2560, "height": 1440},
        ]
        return random.choice(viewports)

    def get_browser_headers(self) -> Dict[str, str]:
        """
        Generate complete, realistic HTTP headers that match this fingerprint.
        Incomplete headers are a primary indicator of bot scrapers.
        """
        is_chrome = "Chrome" in self.user_agent and "Firefox" not in self.user_agent

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": self.accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }

        if is_chrome:
            # Sec-Fetch headers (Chrome-specific)
            headers.update({
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Sec-Ch-Ua-Platform": self.platform_info.get("sec_ch_ua_platform", '"Windows"'),
                "Sec-Ch-Ua-Mobile": "?0",
            })

            # Extract Chrome version for Sec-Ch-Ua
            chrome_ver = "131"
            if "Chrome/" in self.user_agent:
                try:
                    chrome_ver = self.user_agent.split("Chrome/")[1].split(".")[0]
                except (IndexError, ValueError):
                    pass

            headers["Sec-Ch-Ua"] = f'"Chromium";v="{chrome_ver}", "Google Chrome";v="{chrome_ver}", "Not_A Brand";v="24"'

        return headers

    def get_xhr_headers(self, referer: str = "") -> Dict[str, str]:
        """Generate headers for XHR/API requests (after page load)."""
        headers = self.get_browser_headers()
        headers.update({
            "Accept": "*/*",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Requested-With": "XMLHttpRequest",
        })
        if referer:
            headers["Referer"] = referer
        # Remove navigation-specific headers
        headers.pop("Upgrade-Insecure-Requests", None)
        headers.pop("Sec-Fetch-User", None)
        return headers


class FingerprintManager:
    """Manages a pool of fingerprint profiles for rotation."""

    def __init__(self):
        self._profiles: list[FingerprintProfile] = []
        self._current_index = 0

    def get_new_profile(self) -> FingerprintProfile:
        """Create and return a new random fingerprint profile."""
        profile = FingerprintProfile()
        logger.debug(f"Generated fingerprint: UA={profile.user_agent[:60]}...")
        return profile

    def get_rotated_profile(self) -> FingerprintProfile:
        """Get a profile with rotation (creates new periodically)."""
        # Refresh pool every 10 uses
        if not self._profiles or self._current_index >= len(self._profiles):
            self._profiles = [FingerprintProfile() for _ in range(5)]
            self._current_index = 0

        profile = self._profiles[self._current_index]
        self._current_index += 1
        return profile


# Singleton
fingerprint_manager = FingerprintManager()
