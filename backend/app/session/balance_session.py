from sqlalchemy.orm import Session
from app.table.balance_table import Balance
from typing import Optional, List, Sequence

from app.table.balance_summary_view import BalanceSummary

class BalanceSession:
    def __init__(self, db: Session):
        self.db = db

    def create(self, balance_data: dict) -> Balance:
        db_balance = Balance(**balance_data)
        self.db.add(db_balance)
        self.db.commit()
        self.db.refresh(db_balance)
        return db_balance
    
    def update(self, account_number: str, split_level: int, stock_code: str, update_data: dict) -> Optional[Balance]:
        db_balance = self.get(account_number, split_level, stock_code)
        if db_balance:
            for key, value in update_data.items():
                setattr(db_balance, key, value)
            self.db.commit()
            self.db.refresh(db_balance)
        return db_balance

    def delete(self, account_number: str, split_level: int, stock_code: str) -> bool:
        db_balance = self.get(account_number, split_level, stock_code)
        if db_balance:
            self.db.delete(db_balance)
            self.db.commit()
            return True
        return False

    def get(self, account_number: str, split_level: int, stock_code: str) -> Optional[Balance]:
        return self.db.query(Balance).filter(
            Balance.account_number == account_number,
            Balance.split_level == split_level,
            Balance.stock_code == stock_code
        ).first()

    def get_by_account(self, account_number: str) -> List[Balance]:
        return self.db.query(Balance).filter(Balance.account_number == account_number).all()

    def get_by_account_and_stock(self, account_number: str, stock_code: str) -> List[Balance]:
        return self.db.query(Balance).filter(
            Balance.account_number == account_number,
            Balance.stock_code == stock_code
        ).order_by(Balance.split_level).all()

    def get_investment_by_account(self, account_number: str) -> List[BalanceSummary]:
        return self.db.query(BalanceSummary).filter(BalanceSummary.account_number == account_number).all()