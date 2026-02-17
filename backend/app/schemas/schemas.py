from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

class SystemSettingBase(BaseModel):
    account_num: str
    app_key: str
    app_secret: str
    is_virtual: bool = True
    default_gap_ratio: float = 0.03
    default_target_return: float = 0.05

class SystemSetting(SystemSettingBase):
    class Config:
        from_attributes = True

class StockStrategyBase(BaseModel):
    stock_code: str
    stock_name: str
    gap_ratio: float
    target_return: float
    invest_per_split: int
    max_split: int = 7

class StockStrategyCreate(StockStrategyBase):
    pass

class StockStrategy(StockStrategyBase):
    id: int
    status: str

    class Config:
        from_attributes = True

class VirtualBalanceBase(BaseModel):
    stock_code: str
    split_number: int
    quantity: int
    avg_price: int

class VirtualBalance(VirtualBalanceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TradeHistoryBase(BaseModel):
    stock_code: str
    trade_type: str
    split_number: int
    price: int
    quantity: int
    realized_profit: Optional[int] = None

class TradeHistory(TradeHistoryBase):
    id: int
    trade_time: datetime

    class Config:
        from_attributes = True

class CashFlowBase(BaseModel):
    flow_type: str
    amount: int
    memo: Optional[str] = None

class CashFlow(CashFlowBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DailySummary(BaseModel):
    date: date
    total_asset: int
    total_invested: int
    daily_profit: int

    class Config:
        from_attributes = True
