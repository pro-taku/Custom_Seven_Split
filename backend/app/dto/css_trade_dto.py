from typing import Optional

from pydantic import BaseModel, Field


class CreateStrategyRequest(BaseModel):
    stock_code: str = Field(..., example="005930")
    invested_capital: int = Field(..., example=1000000)
    buy_price: int = Field(..., example=60000)
    buy_per: float = Field(0.97, example=0.97)
    first_sell_per: float = Field(1.1, example=1.1)
    sell_per: float = Field(1.05, example=1.05)


class ChangeStrategyRequestDto(BaseModel):
    buy_price: Optional[int] = Field(None, example=59000)
    buy_per: Optional[float] = Field(None, example=0.98)
    first_sell_per: Optional[float] = Field(None, example=1.12)
    sell_per: Optional[float] = Field(None, example=1.06)
