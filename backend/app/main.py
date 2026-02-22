# from fastapi import FastAPI, Depends
# from contextlib import asynccontextmanager
# from sqlalchemy.orm import Session
# from app.db.session import engine, get_db
# from app.models import base
# from app.api.endpoints import strategy, asset, settings
# from app.services.scheduler import setup_scheduler
# from app.db.asset_history_db import AssetHistoryDB # Import AssetHistoryDB

import sys
import os
import logging

# 현재 파일(main.py)의 상위 상위 디렉토리(backend)를 sys.path에 추가하여 'app' 모듈을 찾을 수 있게 함
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db, engine, Base
from app.db.asset_history_db import AssetHistoryDB

logger = logging.getLogger(__name__)

# 앱 모듈이 처음 import 됐을 때, DB와 테이블이 없으면 새로 만든다.
Base.metadata.create_all(bind=engine)

# # 앱의 생명주기에 따라 실행할 함수 (비동기)
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup: Setup scheduler
#     scheduler = setup_scheduler()
#     yield
#     # Shutdown: Stop scheduler
#     scheduler.shutdown()

app = FastAPI(
    # title="Custom Seven Split API",
    # description="API for automating the Seven Split investment strategy.",
    # version="0.1.0",
    # lifespan=lifespan
)

# # Include Routers
# app.include_router(strategy.router, prefix="/api/strategy", tags=["Strategy"])
# app.include_router(asset.router, prefix="/api/asset", tags=["Asset"])
# app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])

@app.get("/", tags=["Root"])
def read_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Welcome to the Custom Seven Split API!"}

@app.get("/test-asset-history", tags=["Test"])
def test_add_asset_history(db: Session = Depends(get_db)):
    """
    Test endpoint to add a new row to AssetHistoryDB.
    """
    try:
        AssetHistoryDB.create(
            db=db,
            invested_capital=1000000,
            total_asset_value=1050000,
            cash_balance=50000,
            net_cash_flow=0,
            dividend=0,
            interest=0,
            stock_pnl=50000,
            total_pnl=50000,
            net_asset_change=50000
        )
        a = AssetHistoryDB.get_all(db=db)
        logger.info(a)
        return {"message": "AssetHistoryDB record created successfully", "record": a}
    except Exception as e:
        db.rollback()
        return {"message": f"Failed to create AssetHistoryDB record: {e}"}
