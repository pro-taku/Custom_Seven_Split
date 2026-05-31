from sqlalchemy import func
from sqlalchemy.orm import Session
from app.table.profit_table import Profit
from typing import Optional, List

class ProfitSession:
    def __init__(self, db: Session):
        self.db = db

    def create(self, profit_data: dict) -> Profit:
        db_profit = Profit(**profit_data)
        self.db.add(db_profit)
        self.db.commit()
        self.db.refresh(db_profit)
        return db_profit
    
    def update(self, buy_odno: str, sell_odno: str, profit: int) -> Optional[Profit]:
        db_profit = self.db.query(Profit).filter(
            Profit.buy_odno == buy_odno, Profit.sell_odno == sell_odno).first()
        if db_profit:
            db_profit.profit = profit
            db_profit.updated_at = None  # 현재 날짜로 업데이트
            self.db.commit()
            self.db.refresh(db_profit)
            return db_profit
        return None

    def get_sum_profit_by_account_and_stock(self, account_number: str, stock_code: str) -> int:
        total_profit = self.db.query(Profit).filter(
            Profit.account_number == account_number,
            Profit.stock_code == stock_code
        ).with_entities(func.sum(Profit.profit)).scalar()
        return total_profit or 0