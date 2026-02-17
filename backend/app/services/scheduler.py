from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.trade_engine import TradeEngine
from app.db.session import SessionLocal
import logging

logger = logging.getLogger(__name__)

async def trade_job():
    logger.info("Starting scheduled trade job...")
    db = SessionLocal()
    try:
        engine = TradeEngine(db)
        await engine.run_logic()
    except Exception as e:
        logger.error(f"Error in trade_job: {e}")
    finally:
        db.close()

def setup_scheduler():
    scheduler = AsyncIOScheduler()
    # Run every 1 minute during market hours (simplified for now: every 1 min always)
    scheduler.add_job(trade_job, 'interval', minutes=1)
    scheduler.start()
    logger.info("Scheduler started.")
    return scheduler
