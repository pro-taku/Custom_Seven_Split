
import datetime as dt
from typing import List, Optional
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session
from ..db.session import Base


class TradeCheckDB(Base):
    __tablename__ = "trade_check_db"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=dt.datetime.now)
    stock_code = Column(String)
    type = Column(String)  # BUY, SELL
    price = Column(Integer)
    count = Column(Integer)
    status = Column(Integer)  # 0=대기중, 1=체결, 2=취소

    def __repr__(self):
        return f"<TradeCheckDB(id={self.id}, stock_code='{self.stock_code}', type='{self.type}')>"

    @classmethod
    def create(cls, db: Session, stock_code: str, trade_type: str, price: int, count: int, status: int):
        new_trade = cls(stock_code=stock_code, type=trade_type, price=price, count=count, status=status)
        db.add(new_trade)
        db.commit()
        db.refresh(new_trade)
        return new_trade

    @classmethod
    def get(cls, db: Session, trade_id: int):
        return db.query(cls).filter(cls.id == trade_id).first()
    
    @classmethod
    def get_all(cls, db: Session) -> List['TradeCheckDB']:
        return db.query(cls).all()

    @classmethod
    def update(cls, db: Session, trade_id: int, **kwargs):
        trade_record = db.query(cls).filter(cls.id == trade_id).first()
        if trade_record:
            for key, value in kwargs.items():
                setattr(trade_record, key, value)
            db.commit()
            db.refresh(trade_record)
            return trade_record
        return None

    @classmethod
    def delete(cls, db: Session, trade_id: int):
        trade_record = db.query(cls).filter(cls.id == trade_id).first()
        if trade_record:
            db.delete(trade_record)
            db.commit()
            return True
        return False

    @classmethod
    def select_in_period(cls, db: Session, start_date: dt.datetime, end_date: dt.datetime) -> List['TradeCheckDB']:
        return db.query(cls).filter(cls.created_at >= start_date, cls.created_at <= end_date).all()

    @classmethod
    def select_by_stock_code(cls, db: Session, stock_code: str) -> List['TradeCheckDB']:
        return db.query(cls).filter(cls.stock_code == stock_code).all()
