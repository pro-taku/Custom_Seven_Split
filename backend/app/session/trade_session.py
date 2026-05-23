from sqlalchemy.orm import Session
from app.table.trade_table import Trade
from typing import Optional, List
from datetime import datetime

class TradeSession:
    def __init__(self, db: Session):
        self.db = db

    def create(self, trade_data: dict) -> Trade:
        db_trade = Trade(**trade_data)
        self.db.add(db_trade)
        self.db.commit()
        self.db.refresh(db_trade)
        return db_trade

    def get_by_account(self, account_number: str) -> List[Trade]:
        return self.db.query(Trade).filter(Trade.account_number == account_number).all()

    def update_status(self, date: datetime, account_number: str, status: str) -> Optional[Trade]:
        db_trade = self.db.query(Trade).filter(
            Trade.date == date,
            Trade.account_number == account_number
        ).first()
        if db_trade:
            db_trade.status = status
            self.db.commit()
            self.db.refresh(db_trade)
        return db_trade
