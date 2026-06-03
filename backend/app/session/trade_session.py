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
    
    def update_status(self, odno: str, status: str) -> Optional[Trade]:
        db_trade = self.db.query(Trade).filter(Trade.odno == odno).first()
        if db_trade:
            db_trade.status = status
            self.db.commit()
            self.db.refresh(db_trade)
        return db_trade
    
    def get_by_odno(self, odno: str) -> Optional[Trade]:
        return self.db.query(Trade).filter(Trade.odno == odno).first()

    def get_by_filter(
        self,
        account_number: str, 
        stock_code: Optional[str] = None, 
        status: Optional[str] = None,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        order_by: Optional[str] = None
    ) -> List[Trade]:
        query = self.db.query(Trade).filter(Trade.account_number == account_number)
        
        if stock_code:
            query = query.filter(Trade.stock_code == stock_code)
        if status:
            query = query.filter(Trade.status == status)
        if start_datetime:
            query = query.filter(Trade.created_at >= start_datetime)
        if end_datetime:
            query = query.filter(Trade.created_at <= end_datetime)
        if order_by:
            if order_by == "desc":
                query = query.order_by(Trade.created_at.desc())
            elif order_by == "asc":
                query = query.order_by(Trade.created_at.asc())
                
        return query.all()

    def get_unexecuted_trades(self, account_number: str) -> List[Trade]:
        return self.db.query(Trade).filter(
            Trade.account_number == account_number,
            Trade.status == 'W'  # 'W' for Waiting
        ).all()
