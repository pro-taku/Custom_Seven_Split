from pydantic import BaseModel, Field


class OrderRequestDto(BaseModel):
    stock_code: str = Field(..., example="005930")
    quantity: int = Field(..., gt=0, example=10)
    price: int = Field(..., gt=0, example=60000)
    side: str = Field("BUY", example="BUY")  # BUY or SELL
    order_division: str = Field("00", example="00")


class ModifyOrderRequestDto(BaseModel):
    original_order_no: str = Field(..., example="0000000001")
    stock_code: str = Field(..., example="005930")
    new_quantity: int = Field(..., gt=0, example=15)
    new_price: int = Field(..., gt=0, example=59500)
    order_division: str = Field("00", example="00")


class CancelOrderRequestDto(BaseModel):
    original_order_no: str = Field(..., example="0000000001")
    order_division: str = Field("00", example="00")