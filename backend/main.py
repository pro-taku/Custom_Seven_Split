from fastapi import FastAPI
from app.core.connect import engine, Base
# 모든 테이블 모델을 임포트하여 metadata에 등록되도록 합니다.
from app.table.user_table import User
from app.table.account_table import Account
from app.table.strategy_table import Strategy
from app.table.balance_table import Balance
from app.table.history_table import History
from app.table.stock_table import Stock
from app.table.trade_table import Trade
from app.table.profit_table import Profit
from app.table.strategy_count_view import StrategyCountView

# DB 테이블 및 뷰 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Seven Split API")

@app.get("/")
def read_root():
    return {"message": "Welcome to Seven Split API"}
