"""
FastAPI application entry point.
Mounts all API routes, serves frontend static files, and manages lifecycle.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.database import init_db
from backend.scraper.engine import scraper_engine
from backend.scheduler.polling import polling_scheduler
from backend.api.routes_posts import router as posts_router
from backend.api.routes_keywords import router as keywords_router
from backend.api.routes_settings import router as settings_router
from backend.api.routes_auth import router as auth_router
from backend.api.routes_scraper import router as scraper_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    logger.info("🚀 Starting Threads Scraper Bot...")
    await init_db()
    logger.info("✅ Database initialized")

    try:
        await scraper_engine.initialize()
        logger.info("✅ Scraper engine initialized")
    except Exception as e:
        logger.warning(f"⚠️ Scraper engine init deferred: {e}")

    # Load saved sessions from DB
    try:
        from backend.database import async_session
        from backend.models import ThreadsAccount
        from sqlalchemy import select
        from backend.scraper.session_manager import session_manager
        from backend.config import settings

        async with async_session() as session:
            result = await session.execute(
                select(ThreadsAccount).where(ThreadsAccount.is_active == True)
            )
            accounts = result.scalars().all()
            for acc in accounts:
                if acc.cookies_json:
                    session_manager.set_cookies_from_json(acc.username, acc.cookies_json)
                    logger.info(f"✅ Loaded session for @{acc.username}")
                if acc.login_status == "logged_in":
                    settings.threads_username = acc.username
    except Exception as e:
        logger.warning(f"⚠️ Session restore: {e}")

    logger.info("🎉 Threads Scraper Bot ready!")

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    await polling_scheduler.stop()
    await scraper_engine.shutdown()
    logger.info("👋 Goodbye!")


# Create FastAPI app
app = FastAPI(
    title="Threads Scraper Bot",
    description="Advanced Threads scraper with anti-detection and web GUI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(posts_router)
app.include_router(keywords_router)
app.include_router(settings_router)
app.include_router(auth_router)
app.include_router(scraper_router)


# Health check
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "threads-scraper-bot",
        "version": "1.0.0",
    }


# Serve frontend
app.mount("/assets", StaticFiles(directory="frontend/assets"), name="assets")
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str = ""):
    """Serve the SPA frontend for all non-API routes."""
    return FileResponse("frontend/index.html")
