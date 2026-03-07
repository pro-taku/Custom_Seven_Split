from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dto.stock_dto import (
    CancelOrderRequestDto,
    ModifyOrderRequestDto,
    OrderRequestDto,
)
from app.services.stock_service import StockService

router = APIRouter()


@router.post("/order")
async def order(
    request: OrderRequestDto,
    db: Session = Depends(get_db),
):
    service = StockService(db)
    return await service.order(
        stock_code=request.stock_code,
        quantity=request.quantity,
        price=request.price,
        side=request.side,
        order_division=request.order_division,
    )


@router.put("/order/modify")
async def modify_order(
    request: ModifyOrderRequestDto,
    db: Session = Depends(get_db),
):
    service = StockService(db)
    return await service.modify_order(
        original_order_no=request.original_order_no,
        stock_code=request.stock_code,
        new_quantity=request.new_quantity,
        new_price=request.new_price,
        order_division=request.order_division,
    )


@router.post("/order/cancel")
async def cancel_order(
    request: CancelOrderRequestDto,
    db: Session = Depends(get_db),
):
    service = StockService(db)
    return await service.cancel_order(
        original_order_no=request.original_order_no,
        order_division=request.order_division,
    )


@router.get("/orders")
async def get_orders(
    order_date: str,
    product_code: str = "",
    db: Session = Depends(get_db),
):
    service = StockService(db)
    return await service.get_orders(order_date=order_date, product_code=product_code)
