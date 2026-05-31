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
    
    def delete(self, date: datetime, account_number: str) -> bool:
        db_history = self.db.query(History).filter(
            History.date == date,
            History.account_number == account_number,
        ).first()
        if db_history:
            self.db.delete(db_history)
            self.db.commit()
            return True
        return False

    def get_by_filter(
        self,
        account_number: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> List[History]:
        query = self.db.query(History).filter(History.account_number == account_number)
        if start_date:
            query = query.filter(History.date >= start_date)
        if end_date:
            query = query.filter(History.date <= end_date)
        return query.all()

