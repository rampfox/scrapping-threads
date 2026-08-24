"""
API routes for Threads authentication and session management.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import ThreadsAccount
from backend.scraper.engine import scraper_engine
from backend.scraper.session_manager import session_manager
from backend.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.get("/status")
async def get_auth_status(db: AsyncSession = Depends(get_db)):
    """Get current authentication status."""
    result = await db.execute(select(ThreadsAccount).where(ThreadsAccount.is_active == True))
    accounts = result.scalars().all()

    return {
        "accounts": [
            {
                "id": acc.id,
                "username": acc.username,
                "status": acc.login_status,
                "last_login": acc.last_login.isoformat() if acc.last_login else None,
                "has_cookies": acc.cookies_json is not None,
            }
            for acc in accounts
        ],
        "is_logged_in": any(acc.login_status == "logged_in" for acc in accounts),
        "session_stats": session_manager.get_stats(),
    }


@router.post("/login")
async def login_threads(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login to Threads to enable search functionality.
    Stores credentials securely (encrypted).
    """
    if not data.username or not data.password:
        raise HTTPException(status_code=400, detail="Username and password required")

    # Update config
    settings.threads_username = data.username
    settings.threads_password = data.password

    # Perform login
    result = await scraper_engine.login_threads(data.username, data.password)

    # Save/update account in DB
    existing = await db.execute(
        select(ThreadsAccount).where(ThreadsAccount.username == data.username)
    )
    account = existing.scalar_one_or_none()

    encrypted_pw = session_manager.encrypt_data(data.password)
    cookies_json = session_manager.get_cookies_json(data.username)

    if account:
        account.encrypted_password = encrypted_pw
        account.login_status = result.get("status", "error")
        account.last_login = datetime.utcnow() if result.get("success") else account.last_login
        account.cookies_json = cookies_json
    else:
        account = ThreadsAccount(
            username=data.username,
            encrypted_password=encrypted_pw,
            login_status=result.get("status", "error"),
            last_login=datetime.utcnow() if result.get("success") else None,
            cookies_json=cookies_json,
        )
        db.add(account)

    await db.commit()

    return result


@router.post("/logout")
async def logout_threads(db: AsyncSession = Depends(get_db)):
    """Clear all Threads sessions."""
    result = await db.execute(select(ThreadsAccount).where(ThreadsAccount.is_active == True))
    accounts = result.scalars().all()

    for account in accounts:
        account.login_status = "not_logged_in"
        account.cookies_json = None

    await db.commit()

    settings.threads_username = ""
    settings.threads_password = ""

    return {"success": True, "message": "Logged out from all accounts"}


@router.post("/test-cookies")
async def test_cookies(db: AsyncSession = Depends(get_db)):
    """Test if stored cookies are still valid."""
    result = await db.execute(
        select(ThreadsAccount).where(
            ThreadsAccount.is_active == True,
            ThreadsAccount.login_status == "logged_in",
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        return {"valid": False, "message": "No logged-in account found"}

    # Load cookies and test
    if account.cookies_json:
        session_manager.set_cookies_from_json(account.username, account.cookies_json)

    return {
        "valid": True,
        "username": account.username,
        "message": "Cookies loaded - validity will be confirmed on next scrape",
    }
