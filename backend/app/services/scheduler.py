from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.trade_engine import TradeEngine
from app.services.asset_manager import AssetManager # Added for daily summary
from app.db.session import SessionLocal
import logging

logger = logging.getLogger(__name__)

# 매일 매매 주문 넣기 스케줄러
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

# 일별 자산 스넵샷 스케줄러
async def daily_summary_job():
    logger.info("Starting daily summary job...")
    db = SessionLocal()
    try:
        asset_manager = AssetManager(db)
        await asset_manager.update_daily_summary()
    except Exception as e:
        logger.error(f"Error in daily_summary_job: {e}")
    finally:
        db.close()

# 스케줄러 등록
def setup_scheduler():
    scheduler = AsyncIOScheduler()
    # Run trade logic every 1 minute during market hours (simplified for now: every 1 min always)
    scheduler.add_job(trade_job, 'interval', minutes=1)
    # Run daily summary update once a day at 23:59
    scheduler.add_job(daily_summary_job, 'cron', hour=23, minute=59)
    scheduler.start()
    logger.info("Scheduler started.")
    return scheduler
