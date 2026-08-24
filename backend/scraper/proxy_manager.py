"""
Proxy rotation and pool management.
Supports HTTP, HTTPS, and SOCKS5 proxies with health checking.
"""
import random
import asyncio
import time
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ProxyInfo:
    """Information about a single proxy."""
    url: str
    protocol: str = "http"
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    is_healthy: bool = True
    last_used: float = 0.0
    fail_count: int = 0
    success_count: int = 0
    avg_response_time: float = 0.0


# Well-known free proxy list URLs (for testing only)
FREE_PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
]


class ProxyManager:
    """
    Manages proxy rotation with health checking and session affinity.
    """

    def __init__(self):
        self._proxies: List[ProxyInfo] = []
        self._session_proxies: Dict[str, ProxyInfo] = {}  # session_id -> proxy
        self._lock = asyncio.Lock()
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled and len(self._proxies) > 0

    @property
    def proxy_count(self) -> int:
        return len(self._proxies)

    @property
    def healthy_count(self) -> int:
        return sum(1 for p in self._proxies if p.is_healthy)

    def load_from_list(self, proxy_strings: List[str]) -> int:
        """
        Load proxies from a list of proxy strings.
        Format: protocol://user:pass@host:port or host:port
        """
        loaded = 0
        for proxy_str in proxy_strings:
            proxy_str = proxy_str.strip()
            if not proxy_str or proxy_str.startswith("#"):
                continue

            try:
                proxy = self._parse_proxy(proxy_str)
                if proxy:
                    self._proxies.append(proxy)
                    loaded += 1
            except Exception as e:
                logger.warning(f"Failed to parse proxy: {proxy_str} - {e}")

        self._enabled = loaded > 0
        logger.info(f"Loaded {loaded} proxies")
        return loaded

    async def load_from_url(self, url: str) -> int:
        """Load proxy list from a URL."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                lines = resp.text.strip().split("\n")
                proxy_strings = [f"http://{line.strip()}" for line in lines if line.strip()]
                return self.load_from_list(proxy_strings)
        except Exception as e:
            logger.error(f"Failed to load proxies from URL {url}: {e}")
            return 0

    async def load_free_proxies(self) -> int:
        """Load free proxies for testing (low quality, not for production)."""
        total = 0
        for source_url in FREE_PROXY_SOURCES:
            count = await self.load_from_url(source_url)
            total += count
            if total >= 50:  # Limit free proxies
                break
        logger.info(f"Loaded {total} free proxies for testing")
        return total

    def _parse_proxy(self, proxy_str: str) -> Optional[ProxyInfo]:
        """Parse a proxy string into ProxyInfo."""
        proxy = ProxyInfo(url=proxy_str)

        if "://" in proxy_str:
            protocol, rest = proxy_str.split("://", 1)
            proxy.protocol = protocol.lower()
        else:
            rest = proxy_str
            proxy.protocol = "http"
            proxy.url = f"http://{proxy_str}"

        # Parse auth
        if "@" in rest:
            auth, hostport = rest.rsplit("@", 1)
            if ":" in auth:
                proxy.username, proxy.password = auth.split(":", 1)
        else:
            hostport = rest

        # Parse host:port
        if ":" in hostport:
            proxy.host, port_str = hostport.rsplit(":", 1)
            proxy.port = int(port_str)
        else:
            proxy.host = hostport
            proxy.port = 8080

        return proxy

    def get_proxy(self, session_id: Optional[str] = None) -> Optional[ProxyInfo]:
        """
        Get a proxy for use, with optional session affinity.
        Rotation strategy: least-recently-used among healthy proxies.
        """
        if not self.is_enabled:
            return None

        # Session affinity: reuse same proxy for same session
        if session_id and session_id in self._session_proxies:
            proxy = self._session_proxies[session_id]
            if proxy.is_healthy:
                return proxy

        # Filter healthy proxies
        healthy = [p for p in self._proxies if p.is_healthy]
        if not healthy:
            # Reset all proxies if none healthy
            logger.warning("No healthy proxies, resetting all")
            for p in self._proxies:
                p.is_healthy = True
                p.fail_count = 0
            healthy = self._proxies

        # Least recently used
        proxy = min(healthy, key=lambda p: p.last_used)
        proxy.last_used = time.time()

        if session_id:
            self._session_proxies[session_id] = proxy

        return proxy

    def get_playwright_proxy(self, session_id: Optional[str] = None) -> Optional[Dict]:
        """Get proxy config formatted for Playwright."""
        proxy = self.get_proxy(session_id)
        if not proxy:
            return None

        config = {
            "server": f"{proxy.protocol}://{proxy.host}:{proxy.port}",
        }
        if proxy.username:
            config["username"] = proxy.username
            config["password"] = proxy.password

        return config

    def report_success(self, proxy: ProxyInfo) -> None:
        """Report successful use of a proxy."""
        proxy.success_count += 1
        proxy.fail_count = max(0, proxy.fail_count - 1)

    def report_failure(self, proxy: ProxyInfo) -> None:
        """Report failed use of a proxy."""
        proxy.fail_count += 1
        if proxy.fail_count >= 3:
            proxy.is_healthy = False
            logger.warning(f"Proxy marked unhealthy: {proxy.host}:{proxy.port}")

    def release_session(self, session_id: str) -> None:
        """Release session affinity for a proxy."""
        self._session_proxies.pop(session_id, None)

    def get_stats(self) -> Dict:
        """Get proxy pool statistics."""
        return {
            "enabled": self._enabled,
            "total": len(self._proxies),
            "healthy": self.healthy_count,
            "active_sessions": len(self._session_proxies),
        }

    def clear(self) -> None:
        """Clear all proxies."""
        self._proxies.clear()
        self._session_proxies.clear()
        self._enabled = False


# Singleton
proxy_manager = ProxyManager()
