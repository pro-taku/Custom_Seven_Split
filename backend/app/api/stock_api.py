from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.stock_service import StockService

router = APIRouter()

@router.get("/{stock_code}/price")
async def get_current_price(stock_code: str, db: Session = Depends(get_db)):
    service = StockService(db)
    price = await service.get_current_price(stock_code)
    return {"stock_code": stock_code, "current_price": price}

@router.post("/order")
async def order(
    stock_code: str,
    quantity: int,
    price: int,
    side: str = "BUY",
    order_division: str = "00",
    db: Session = Depends(get_db),
):
    service = StockService(db)
    return await service.order(
        stock_code=stock_code,
        quantity=quantity,
        price=price,
        side=side,
        order_division=order_division,
    )

@router.put("/order/modify")
async def modify_order(
    original_order_no: str,
    stock_code: str,
    new_quantity: int,
    new_price: int,
    order_division: str = "00",
    db: Session = Depends(get_db),
):
    service = StockService(db)
    return await service.modify_order(
        original_order_no=original_order_no,
        stock_code=stock_code,
        new_quantity=new_quantity,
        new_price=new_price,
        order_division=order_division,
    )

@router.post("/order/cancel")
async def cancel_order(
    original_order_no: str,
    order_division: str = "00",
    db: Session = Depends(get_db),
):
    service = StockService(db)
    return await service.cancel_order(
        original_order_no=original_order_no,
        order_division=order_division,
    )

@router.get("/orders")
async def get_orders(
    order_date: str,
    product_code: str = "",
    db: Session = Depends(get_db),
):
    service = StockService(db)
    return await service.get_orders(order_date=order_date, product_code=product_code)

@router.get("/{stock_code}/info")
async def get_stock_info(stock_code: str, db: Session = Depends(get_db)):
    service = StockService(db)
    return await service.get_stock_info(stock_code)
