from sqlalchemy.orm import Session
from app.table.history_table import History
from typing import List
from datetime import datetime

class HistorySession:
    def __init__(self, db: Session):
        self.db = db

    def create(self, history_data: dict) -> History:
        db_history = History(**history_data)
        self.db.add(db_history)
        self.db.commit()
        self.db.refresh(db_history)
        return db_history

    def get_by_account(self, account_number: str) -> List[History]:
        return self.db.query(History).filter(History.account_number == account_number).all()

    def delete(self, date: datetime, account_number: str, split_level: int) -> bool:
        db_history = self.db.query(History).filter(
            History.date == date,
            History.account_number == account_number,
            History.split_level == split_level
        ).first()
        if db_history:
            self.db.delete(db_history)
            self.db.commit()
            return True
        return False
