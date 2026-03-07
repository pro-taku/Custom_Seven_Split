from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.app.core.websocket import CSSWebSocket
from backend.app.lib.kis.client import KISClient
from backend.app.services.asset_service import AssetService
from backend.app.services.stock_service import StockService
from fastapi.logger import logger

from app.core.config import GLOBAL_ENV, IS_HOLIDAY, SessionLocal, TradeStatus


# 개장일 8시 반에 주문 넣기
async def process_trade_scheduling():
    db = SessionLocal()
    stock_service = StockService(db)

    try:
        if IS_HOLIDAY:
            await stock_service.is_today_holiday()
            if IS_HOLIDAY:
                logger.info("오늘은 휴장일입니다. 주문을 처리하지 않습니다.")
                return

        # 체결 대기 중인 주문만 조회
        orders = await stock_service.get_orders(
            status=TradeStatus.PENDING.value,
        )
        for order in orders:
            try:
                await stock_service.order(
                    trade_id=order.trade_id,
                    stock_code=order.stock_code,
                    quantity=order.count,
                    price=order.price,
                    trade_type=order.trade_type,
                    split_level=order.split_level,
                )
                logger.info(f"Order {order.trade_id} processed successfully.")
            except Exception as e:
                logger.error(f"Failed to process order {order.trade_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to fetch pending orders: {e}")
        return


# 개장일 9시에 주문체결여부 확인용 소켓 등록
async def process_socket_registration():
    kis = KISClient(env=GLOBAL_ENV)
    ws = CSSWebSocket(ws_url=kis.ws_domain)

    try:
        # 다음 API를 웹소켓에 등록한다:
        # https://apiportal.koreainvestment.com/apiservice-apiservice?/tryitout/H0STCNI0
        pass
    except Exception as e:
        logger.error(f"Failed to register WebSocket: {e}")
        return


# 개장일 15시 반에 소켓 해제
async def process_socket_unregistration():
    kis = KISClient(env=GLOBAL_ENV)
    ws = CSSWebSocket(ws_url=kis.ws_domain)

    try:
        # 웹소켓 해제 로직을 여기에 구현한다
        # 예시: await ws._disconnect()
        pass
    except Exception as e:
        logger.error(f"Failed to register WebSocket: {e}")
        return


# 개장일 16시에 자산 스넵샷
async def process_asset_snapshot():
    db = SessionLocal()
    asset_service = AssetService(db)

    try:
        await asset_service.add_asset_history()
    except Exception as e:
        logger.error(f"Failed to add asset history: {e}")
        return


# 스케줄러 등록
def setup_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.start()

    # 개장일 8시 반에 주문 넣기
    scheduler.add_job(process_trade_scheduling, "cron", hour=8, minute=30)

    # 개장일 9시에 주문체결여부 확인용 소켓 등록
    scheduler.add_job(process_socket_registration, "cron", hour=9, minute=0)

    # 개장일 15시 반에 소켓 해제
    scheduler.add_job(process_socket_unregistration, "cron", hour=15, minute=30)

    # 개장일 16시에 자산 스넵샷
    scheduler.add_job(process_asset_snapshot, "cron", hour=16, minute=0)

    logger.info("Scheduler started.")
    return scheduler
