"""
API routes for scraper settings and configuration.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import ScraperSetting
from backend.scheduler.polling import polling_scheduler
from backend.scraper.proxy_manager import proxy_manager
from backend.scraper.captcha_handler import captcha_handler
from backend.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    polling_interval: Optional[int] = None  # 30-600 seconds
    max_concurrent: Optional[int] = None
    proxy_enabled: Optional[bool] = None
    proxy_list: Optional[str] = None
    captcha_service: Optional[str] = None
    captcha_api_key: Optional[str] = None


class ProxyConfig(BaseModel):
    enabled: bool = False
    proxies: List[str] = []
    proxy_url: Optional[str] = None


@router.get("")
async def get_settings():
    """Get current scraper settings."""
    return {
        "polling_interval": polling_scheduler.interval,
        "max_concurrent": settings.max_concurrent,
        "max_keywords": settings.max_keywords,
        "proxy": proxy_manager.get_stats(),
        "captcha": captcha_handler.get_stats(),
        "scheduler": polling_scheduler.get_status(),
    }


@router.put("")
async def update_settings(data: SettingsUpdate):
    """Update scraper settings."""
    results = {}

    if data.polling_interval is not None:
        await polling_scheduler.update_interval(data.polling_interval)
        results["polling_interval"] = polling_scheduler.interval

    if data.proxy_enabled is not None:
        settings.proxy_enabled = data.proxy_enabled
        if data.proxy_enabled and data.proxy_list:
            proxies = [p.strip() for p in data.proxy_list.split(",") if p.strip()]
            count = proxy_manager.load_from_list(proxies)
            results["proxies_loaded"] = count
        elif not data.proxy_enabled:
            results["proxy_status"] = "disabled"

    if data.captcha_service is not None or data.captcha_api_key is not None:
        service = data.captcha_service or captcha_handler.service
        api_key = data.captcha_api_key or captcha_handler.api_key
        captcha_handler.update_config(service, api_key)
        results["captcha"] = captcha_handler.get_stats()

    return {"success": True, "updated": results}


@router.get("/proxy")
async def get_proxy_config():
    """Get proxy configuration details."""
    return proxy_manager.get_stats()


@router.put("/proxy")
async def update_proxy_config(data: ProxyConfig):
    """Update proxy configuration."""
    proxy_manager.clear()

    if data.enabled:
        if data.proxies:
            count = proxy_manager.load_from_list(data.proxies)
        elif data.proxy_url:
            count = await proxy_manager.load_from_url(data.proxy_url)
        else:
            count = await proxy_manager.load_free_proxies()

        settings.proxy_enabled = True
        return {
            "success": True,
            "enabled": True,
            "proxies_loaded": count if 'count' in dir() else 0,
        }
    else:
        settings.proxy_enabled = False
        return {
            "success": True,
            "enabled": False,
            "proxies_loaded": 0,
        }


@router.post("/export")
async def export_data(
    format: str = "json",
    db: AsyncSession = Depends(get_db),
):
    """Export all scraped data as JSON or CSV."""
    from fastapi.responses import Response
    from backend.models import ThreadPost

    result = await db.execute(select(ThreadPost).order_by(ThreadPost.scraped_at.desc()))
    posts = result.scalars().all()

    if format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "username", "display_name", "content", "posted_at",
            "keyword", "url", "likes", "replies"
        ])
        for p in posts:
            writer.writerow([
                p.id, p.username, p.display_name, p.content,
                p.posted_at.isoformat() if p.posted_at else "",
                p.keyword, p.url, p.like_count, p.reply_count,
            ])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=threads_data.csv"},
        )
    else:
        import json
        data = [
            {
                "id": p.id,
                "username": p.username,
                "display_name": p.display_name,
                "content": p.content,
                "posted_at": p.posted_at.isoformat() if p.posted_at else None,
                "keyword": p.keyword,
                "url": p.url,
                "likes": p.like_count,
                "replies": p.reply_count,
            }
            for p in posts
        ]
        return Response(
            content=json.dumps(data, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=threads_data.json"},
        )
