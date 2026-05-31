from sqlalchemy.orm import Session
from app.table.strategy_table import Strategy
from typing import Optional, List

class StrategySession:
    def __init__(self, db: Session):
        self.db = db

    def create(self, strategy_data: dict) -> Strategy:
        db_strategy = Strategy(**strategy_data)
        self.db.add(db_strategy)
        self.db.commit()
        self.db.refresh(db_strategy)
        return db_strategy
    
    def update(self, account_number: str, stock_code: str, update_data: dict) -> Optional[Strategy]:
        db_strategy = self.get(account_number, stock_code)
        if db_strategy:
            for key, value in update_data.items():
                setattr(db_strategy, key, value)
            self.db.commit()
            self.db.refresh(db_strategy)
        return db_strategy

    def delete(self, account_number: str, stock_code: str) -> bool:
        db_strategy = self.get(account_number, stock_code)
        if db_strategy:
            self.db.delete(db_strategy)
            self.db.commit()
            return True
        return False

    def get(self, account_number: str, stock_code: str) -> Optional[Strategy]:
        return self.db.query(Strategy).filter(
            Strategy.account_number == account_number,
            Strategy.stock_code == stock_code
        ).first()

    def get_by_account(self, account_number: str) -> List[Strategy]:
        return self.db.query(Strategy).filter(Strategy.account_number == account_number).all()

