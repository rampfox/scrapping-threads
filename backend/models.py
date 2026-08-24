"""
SQLAlchemy ORM models for the Threads scraper.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, JSON
)
from backend.database import Base


class ThreadPost(Base):
    """Scraped Threads post data."""
    __tablename__ = "thread_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(50), nullable=True)  # Threads post code for URL
    username = Column(String(100), nullable=False, index=True)
    display_name = Column(String(200), nullable=True)
    user_pic = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)
    content = Column(Text, nullable=True)
    posted_at = Column(DateTime, nullable=True, index=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
    keyword = Column(String(200), nullable=True, index=True)
    url = Column(Text, nullable=True)
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    images = Column(JSON, nullable=True)  # List of image URLs
    videos = Column(JSON, nullable=True)  # List of video URLs
    raw_data = Column(JSON, nullable=True)  # Full raw JSON for debugging


class Keyword(Base):
    """Keywords to monitor on Threads."""
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(200), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_scraped_at = Column(DateTime, nullable=True)
    post_count = Column(Integer, default=0)


class ScraperSetting(Base):
    """Scraper configuration stored in DB."""
    __tablename__ = "scraper_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ThreadsAccount(Base):
    """Threads login account for search functionality."""
    __tablename__ = "threads_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    encrypted_password = Column(Text, nullable=True)
    cookies_json = Column(Text, nullable=True)  # Encrypted cookies
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    login_status = Column(String(50), default="not_logged_in")  # not_logged_in, logged_in, expired, error
    created_at = Column(DateTime, default=datetime.utcnow)
