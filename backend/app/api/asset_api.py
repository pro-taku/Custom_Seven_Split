from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.asset_service import AssetService

router = APIRouter()

@router.get("/total")
async def get_total_asset(db: Session = Depends(get_db)):
    service = AssetService(db)
    return await service.get_total_asset()

@router.get("/virtual/{split_level}")
async def get_virtual_account_asset(split_level: int, db: Session = Depends(get_db)):
    service = AssetService(db)
    return await service.get_virtual_account_asset(split_level)

@router.get("/cash-flow")
def get_cash_flow(start_date: datetime, end_date: datetime, db: Session = Depends(get_db)):
    service = AssetService(db)
    return service.get_cash_flow(start_date, end_date)

@router.get("/history")
def get_asset_history(start_date: datetime, end_date: datetime, db: Session = Depends(get_db)):
    service = AssetService(db)
    return service.get_asset_history(start_date, end_date)
