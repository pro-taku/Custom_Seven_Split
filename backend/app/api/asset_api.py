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
def get_cash_flow(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
):
    service = AssetService(db)
    return service.get_cash_flow(start_date, end_date)


@router.post("/cash-flow")
def add_cash_flow(
    deposit: int,
    flow_type: str,
    amount: int,
    db: Session = Depends(get_db),
):
    service = AssetService(db)
    return service.record_cash_flow(
        flow_type=flow_type,
        amount=amount,
        current_deposit=deposit,
    )


@router.delete("/cash-flow/{cash_flow_id}")
def delete_cash_flow(cash_flow_id: int, db: Session = Depends(get_db)):
    service = AssetService(db)
    return service.delete_cash_flow(cash_flow_id)


@router.get("/history")
def get_asset_history(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
):
    service = AssetService(db)
    return service.get_asset_history(start_date, end_date)


@router.put("/history/{history_id}")
async def update_asset_history(
    history_id: int,
    invested_capital: int = None,
    stock_valutation: int = None,
    deposit: int = None,
    net_cash_flow: int = None,
    dividend: int = None,
    interest: int = None,
    stock_profit_loss: int = None,
    total_profit_loss: int = None,
    fund_change: int = None,
    db: Session = Depends(get_db),
):
    # 모든 파라미터가 비어있다면, 400 에러
    if (
        invested_capital is None
        and stock_valutation is None
        and deposit is None
        and net_cash_flow is None
        and dividend is None
        and interest is None
        and stock_profit_loss is None
        and total_profit_loss is None
        and fund_change is None
    ):
        return {"error": "At least one parameter must be provided."}

    service = AssetService(db)
    service.modify_asset_history(
        history_id=history_id,
        invested_capital=invested_capital,
        stock_valutation=stock_valutation,
        deposit=deposit,
        net_cash_flow=net_cash_flow,
        dividend=dividend,
        interest=interest,
        stock_profit_loss=stock_profit_loss,
        total_profit_loss=total_profit_loss,
        fund_change=fund_change,
    )
    return {"message": "Asset history updated successfully."}


@router.delete("/history/{history_id}")
def delete_asset_history(history_id: int, db: Session = Depends(get_db)):
    service = AssetService(db)
    service.delete_asset_history(history_id)
    return {"message": "Asset history deleted successfully."}
