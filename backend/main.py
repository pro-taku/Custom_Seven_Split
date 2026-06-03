import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.connect import engine, Base, SessionLocal
from app.service.scheduler_service import SchedulerService
from app.service.ws_service import KISWebSocketManager

# 모든 테이블 모델 임포트 (metadata 등록용)
from app.table.user_table import User
from app.table.account_table import Account
from app.table.strategy_table import Strategy
from app.table.balance_table import Balance
from app.table.history_table import History
from app.table.stock_table import Stock
from app.table.trade_table import Trade
from app.table.profit_table import Profit
from app.table.strategy_count_view import StrategyCountView

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

# 전역 스케줄러 및 서비스 인스턴스 (방법 A: 싱글톤 유지)
scheduler = AsyncIOScheduler()
# 스케줄러 작업에서 사용할 세션은 작업 실행 시마다 새로 생성하는 것이 좋으나, 
# 여기서는 서비스 인스턴스를 하나로 유지합니다.
scheduler_service = SchedulerService(SessionLocal())

@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 실행될 로직"""
    print("🚀 서버를 시작합니다...")
    
    # 1. 스케줄 등록
    # 매월 1일 00:00 - 원금 업데이트
    scheduler.add_job(
        scheduler_service.update_monthly_principal, 
        CronTrigger(day=1, hour=0, minute=0)
    )
    
    # 매 개장일 08:40 - 주문 요청 및 웹소켓 구독
    scheduler.add_job(
        scheduler_service.request_daily_orders, 
        CronTrigger(day_of_week='mon-fri', hour=8, minute=40)
    )
    
    # 매 개장일 16:00 - 자산추이 업데이트 및 웹소켓 해제
    scheduler.add_job(
        scheduler_service.update_daily_asset_trend, 
        CronTrigger(day_of_week='mon-fri', hour=16, minute=0)
    )
    
    # 2. 스케줄러 시작
    scheduler.start()
    print("⏰ 스케줄러가 시작되었습니다.")

    yield # 앱 실행 중

    # 3. 서버 종료 시 정리
    print("🛑 서버를 종료합니다...")
    scheduler.shutdown()
    await KISWebSocketManager().stop_all()

app = FastAPI(title="Seven Split API", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Welcome to Seven Split API with Scheduler"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
