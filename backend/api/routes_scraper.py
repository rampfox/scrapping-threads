"""
API routes for scraper control and monitoring.
"""
from fastapi import APIRouter
from backend.scraper.engine import scraper_engine
from backend.scheduler.polling import polling_scheduler

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


@router.get("/status")
async def get_scraper_status():
    """Get comprehensive scraper status."""
    return {
        "engine": scraper_engine.get_status(),
        "scheduler": polling_scheduler.get_status(),
    }


@router.post("/start")
async def start_scraper():
    """Start the scraper and scheduler."""
    try:
        if not scraper_engine.is_initialized:
            await scraper_engine.initialize()

        await polling_scheduler.start()

        return {
            "success": True,
            "message": "Scraper started",
            "status": scraper_engine.get_status(),
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@router.post("/stop")
async def stop_scraper():
    """Stop the scraper and scheduler."""
    await polling_scheduler.stop()
    return {
        "success": True,
        "message": "Scraper stopped",
    }


@router.post("/restart")
async def restart_scraper():
    """Restart the scraper."""
    await polling_scheduler.stop()
    await scraper_engine.shutdown()
    await scraper_engine.initialize()
    await polling_scheduler.start()
    return {
        "success": True,
        "message": "Scraper restarted",
    }


@router.get("/logs")
async def get_scraper_logs(limit: int = 50):
    """Get recent scraper logs."""
    return {
        "logs": scraper_engine.get_logs(limit),
    }
