"""
Application configuration management using Pydantic Settings.
Loads from environment variables and .env file.
"""
import os
import secrets
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/threads.db"

    # Threads Account
    threads_username: str = ""
    threads_password: str = ""

    # Proxy
    proxy_list: str = ""  # Comma-separated
    proxy_list_url: str = ""
    proxy_enabled: bool = False

    # CAPTCHA
    captcha_service: str = ""  # 2captcha, anticaptcha
    captcha_api_key: str = ""

    # Scraper
    polling_interval: int = 120  # seconds
    max_concurrent: int = 2
    max_keywords: int = 20

    # Security
    secret_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_secret_key(self) -> str:
        """Get or generate secret key for encryption."""
        if self.secret_key:
            return self.secret_key
        # Auto-generate and persist
        key = secrets.token_hex(32)
        self.secret_key = key
        return key

    def get_proxy_list(self) -> List[str]:
        """Parse comma-separated proxy list."""
        if not self.proxy_list:
            return []
        return [p.strip() for p in self.proxy_list.split(",") if p.strip()]


# Singleton instance
settings = Settings()
