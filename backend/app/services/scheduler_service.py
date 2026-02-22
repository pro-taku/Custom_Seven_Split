from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.css_trade_service import CSSTradeService
from app.services.asset_service import AssetService
from app.db.session import SessionLocal
import logging

logger = logging.getLogger(__name__)

# 매일 매매 주문 넣기 스케줄러 (또는 주기적 체크)
async def trade_job():
    logger.info("Starting scheduled trade job...")
    db = SessionLocal()
    try:
        # Note: 실제 구현에서는 여기서 시장에 진입할지 말지 전체 전략을 스캔하는 
        # run_logic()과 같은 메서드가 필요합니다. 
        # 현재는 check_trade_result가 실시간 웹소켓으로 돈다고 가정하고 있으므로,
        # 이 잡은 주기적 batch check (웹소켓 연결이 끊어졌을 때를 대비한 fallback 등) 로 사용될 수 있습니다.
        trade_service = CSSTradeService(db)
        if trade_service.is_market_open():
            logger.info("Market is open. Running batch trade checks...")
            # Example: check pending orders or execute daily strategies here
            # For now, it's a placeholder until run_logic is fully defined.
            pass 
        else:
            logger.info("Market is closed. Skipping trade job.")
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
    # Run trade logic every 1 minute during market hours
    scheduler.add_job(trade_job, 'interval', minutes=1)
    
    # Run daily summary update once a day at 23:59
    scheduler.add_job(daily_summary_job, 'cron', hour=23, minute=59)
    
    scheduler.start()
    logger.info("Scheduler started.")
    return scheduler