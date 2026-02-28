from fastapi import APIRouter

from .asset_api import router as asset_router
from .css_trade_api import router as css_trade_router
from .stock_api import router as stock_router

api_router = APIRouter()
api_router.include_router(asset_router, prefix="/asset", tags=["asset"])
api_router.include_router(css_trade_router, prefix="/css-trade", tags=["css-trade"])
api_router.include_router(stock_router, prefix="/stock", tags=["stock"])
