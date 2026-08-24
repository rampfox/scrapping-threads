"""
API routes for timeline posts - CRUD and listing with pagination.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import ThreadPost

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("")
async def list_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List scraped posts with pagination and filtering.
    Returns newest first (timeline order).
    """
    query = select(ThreadPost).order_by(desc(ThreadPost.scraped_at))

    # Filter by keyword
    if keyword:
        query = query.where(ThreadPost.keyword == keyword)

    # Search in content
    if search:
        query = query.where(ThreadPost.content.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(ThreadPost)
    if keyword:
        count_query = count_query.where(ThreadPost.keyword == keyword)
    if search:
        count_query = count_query.where(ThreadPost.content.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    posts = result.scalars().all()

    return {
        "posts": [_serialize_post(p) for p in posts],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 0,
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get post statistics."""
    total = await db.execute(select(func.count()).select_from(ThreadPost))
    total_count = total.scalar() or 0

    # Posts today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today = await db.execute(
        select(func.count()).select_from(ThreadPost)
        .where(ThreadPost.scraped_at >= today_start)
    )
    today_count = today.scalar() or 0

    # Unique usernames
    usernames = await db.execute(
        select(func.count(func.distinct(ThreadPost.username))).select_from(ThreadPost)
    )
    username_count = usernames.scalar() or 0

    # Unique keywords
    keywords = await db.execute(
        select(func.count(func.distinct(ThreadPost.keyword))).select_from(ThreadPost)
    )
    keyword_count = keywords.scalar() or 0

    return {
        "total_posts": total_count,
        "posts_today": today_count,
        "unique_users": username_count,
        "unique_keywords": keyword_count,
    }


@router.get("/{post_id}")
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single post by ID."""
    result = await db.execute(
        select(ThreadPost).where(ThreadPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _serialize_post(post)


@router.delete("/{post_id}")
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a single post."""
    result = await db.execute(
        select(ThreadPost).where(ThreadPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await db.delete(post)
    await db.commit()
    return {"success": True, "message": "Post deleted"}


@router.delete("")
async def delete_all_posts(
    keyword: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Delete all posts, optionally filtered by keyword."""
    query = delete(ThreadPost)
    if keyword:
        query = query.where(ThreadPost.keyword == keyword)
    await db.execute(query)
    await db.commit()
    return {"success": True, "message": "Posts deleted"}


def _serialize_post(post: ThreadPost) -> dict:
    """Serialize a ThreadPost to JSON-safe dict."""
    return {
        "id": post.id,
        "thread_id": post.thread_id,
        "code": post.code,
        "username": post.username,
        "display_name": post.display_name,
        "user_pic": post.user_pic,
        "is_verified": post.is_verified,
        "content": post.content,
        "posted_at": post.posted_at.isoformat() if post.posted_at else None,
        "scraped_at": post.scraped_at.isoformat() if post.scraped_at else None,
        "keyword": post.keyword,
        "url": post.url,
        "like_count": post.like_count,
        "reply_count": post.reply_count,
        "images": post.images or [],
        "videos": post.videos or [],
    }
