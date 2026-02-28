import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.session import SessionLocal
from app.services.asset_service import AssetService
from app.services.css_trade_service import CSSTradeService

logger = logging.getLogger(__name__)


# 예약주문 다시 넣기
async def trade_job():
    logger.info("Starting 4-week scheduled reservation order refresh job...")
    db = SessionLocal()
    try:
        trade_service = CSSTradeService(db)
        await trade_service.refresh_strategies()
    except Exception as e:
        logger.error(f"Error in trade_job: {e}")
    finally:
        db.close()


# 일별 자산 스냅샷 스케줄러
async def daily_summary_job():
    logger.info("Starting daily summary job...")
    db = SessionLocal()
    try:
        asset_service = AssetService(db)
        await asset_service.asset_snapshot()
    except Exception as e:
        logger.error(f"Error in daily_summary_job: {e}")
    finally:
        db.close()


# 스케줄러 등록
def setup_scheduler():
    scheduler = AsyncIOScheduler()
    # 4주마다 예약주문 갱신 (28일 간격)
    scheduler.add_job(trade_job, "interval", days=28)

    # Run daily summary update once a day at 23:59
    scheduler.add_job(daily_summary_job, "cron", hour=23, minute=59)

    scheduler.start()
    logger.info("Scheduler started.")
    return scheduler
