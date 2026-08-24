"""
API routes for keyword management.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import Keyword
from backend.scheduler.polling import polling_scheduler
from backend.config import settings

router = APIRouter(prefix="/api/keywords", tags=["keywords"])


class KeywordCreate(BaseModel):
    keyword: str


class KeywordUpdate(BaseModel):
    keyword: str | None = None
    is_active: bool | None = None


@router.get("")
async def list_keywords(db: AsyncSession = Depends(get_db)):
    """List all keywords."""
    result = await db.execute(select(Keyword).order_by(Keyword.created_at.desc()))
    keywords = result.scalars().all()
    return {
        "keywords": [
            {
                "id": kw.id,
                "keyword": kw.keyword,
                "is_active": kw.is_active,
                "created_at": kw.created_at.isoformat() if kw.created_at else None,
                "last_scraped_at": kw.last_scraped_at.isoformat() if kw.last_scraped_at else None,
                "post_count": kw.post_count or 0,
            }
            for kw in keywords
        ],
        "total": len(keywords),
        "max_allowed": settings.max_keywords,
    }


@router.post("")
async def create_keyword(data: KeywordCreate, db: AsyncSession = Depends(get_db)):
    """Add a new keyword to monitor."""
    keyword_text = data.keyword.strip()
    if not keyword_text:
        raise HTTPException(status_code=400, detail="Keyword cannot be empty")

    # Check limit
    count_result = await db.execute(select(func.count()).select_from(Keyword))
    count = count_result.scalar() or 0
    if count >= settings.max_keywords:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_keywords} keywords allowed"
        )

    # Check duplicate
    existing = await db.execute(
        select(Keyword).where(Keyword.keyword == keyword_text)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Keyword already exists")

    kw = Keyword(keyword=keyword_text)
    db.add(kw)
    await db.commit()
    await db.refresh(kw)

    return {
        "success": True,
        "keyword": {
            "id": kw.id,
            "keyword": kw.keyword,
            "is_active": kw.is_active,
            "created_at": kw.created_at.isoformat(),
            "post_count": 0,
        },
    }


@router.put("/{keyword_id}")
async def update_keyword(
    keyword_id: int,
    data: KeywordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a keyword."""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")

    if data.keyword is not None:
        kw.keyword = data.keyword.strip()
    if data.is_active is not None:
        kw.is_active = data.is_active

    await db.commit()
    return {"success": True, "message": "Keyword updated"}


@router.delete("/{keyword_id}")
async def delete_keyword(keyword_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a keyword."""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")

    await db.delete(kw)
    await db.commit()
    return {"success": True, "message": "Keyword deleted"}


@router.post("/{keyword_id}/scrape-now")
async def scrape_keyword_now(keyword_id: int, db: AsyncSession = Depends(get_db)):
    """Trigger immediate scrape for a specific keyword."""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")

    saved = await polling_scheduler.trigger_keyword_scrape(kw.keyword)

    # Update stats
    kw.last_scraped_at = datetime.utcnow()
    kw.post_count = (kw.post_count or 0) + saved
    await db.commit()

    return {
        "success": True,
        "keyword": kw.keyword,
        "new_posts": saved,
        "message": f"Scraped {saved} new posts",
    }
