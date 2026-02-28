from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.css_trade_service import CSSTradeService

router = APIRouter()

@router.post("/strategy")
async def create_strategy(
    stock_code: str,
    invested_capital: int,
    buy_price: int,
    buy_per: float = 0.97,
    first_sell_per: float = 1.1,
    sell_per: float = 1.05,
    db: Session = Depends(get_db),
):
    service = CSSTradeService(db)
    return await service.create_strategy(
        stock_code=stock_code,
        invested_capital=invested_capital,
        buy_price=buy_price,
        buy_per=buy_per,
        first_sell_per=first_sell_per,
        sell_per=sell_per,
    )

@router.put("/strategy/{stock_code}")
def change_strategy(
    stock_code: str,
    buy_price: Optional[int] = None,
    buy_per: Optional[float] = None,
    first_sell_per: Optional[float] = None,
    sell_per: Optional[float] = None,
    db: Session = Depends(get_db),
):
    service = CSSTradeService(db)
    return service.change_strategy(
        stock_code=stock_code,
        buy_price=buy_price,
        buy_per=buy_per,
        first_sell_per=first_sell_per,
        sell_per=sell_per,
    )

@router.delete("/strategy/{stock_code}")
def delete_strategy(stock_code: str, db: Session = Depends(get_db)):
    service = CSSTradeService(db)
    return service.delete_strategy(stock_code)

@router.get("/strategy/all")
def get_strategy_all(db: Session = Depends(get_db)):
    service = CSSTradeService(db)
    return service.get_strategy_all()

@router.get("/strategy/{stock_code}")
def get_strategy(stock_code: str, db: Session = Depends(get_db)):
    service = CSSTradeService(db)
    return service.get_strategy(stock_code)

@router.get("/trade-check")
def get_trade_check_list(
    stock_code: Optional[str] = None,
    status: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    service = CSSTradeService(db)
    return service.get_trade_check_list(
        stock_code=stock_code,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
