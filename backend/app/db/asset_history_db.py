
import datetime as dt
from typing import List, Optional
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session
from ..db.session import Base


class AssetHistoryDB(Base):
    __tablename__ = "asset_history_db"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=dt.datetime.now)
    invested_capital = Column(Integer)
    total_asset_value = Column(Integer)  # Renamed from stock_valutation
    cash_balance = Column(Integer)       # Renamed from deposit
    net_cash_flow = Column(Integer)
    dividend = Column(Integer)
    interest = Column(Integer)
    stock_pnl = Column(Integer)         # Renamed from stock_profit_loss
    total_pnl = Column(Integer)         # Renamed from total_profit_loss
    net_asset_change = Column(Integer)  # Renamed from fund_change

    def __repr__(self):
        return f"<AssetHistoryDB(id={self.id}, created_at={self.created_at}, total_asset_value={self.total_asset_value})>"

    @classmethod
    def create(cls, db: Session, invested_capital: int, total_asset_value: int, cash_balance: int, net_cash_flow: int, dividend: int, interest: int, stock_pnl: int, total_pnl: int, net_asset_change: int):
        new_history = cls(invested_capital=invested_capital, total_asset_value=total_asset_value, cash_balance=cash_balance, net_cash_flow=net_cash_flow, dividend=dividend, interest=interest, stock_pnl=stock_pnl, total_pnl=total_pnl, net_asset_change=net_asset_change)
        db.add(new_history)
        db.commit()
        db.refresh(new_history)
        return new_history

    @classmethod
    def get(cls, db: Session, history_id: int):
        return db.query(cls).filter(cls.id == history_id).first()

    @classmethod
    def get_all(cls, db: Session) -> List['AssetHistoryDB']:
        return db.query(cls).all()

    @classmethod
    def update(cls, db: Session, history_id: int, **kwargs):
        history_record = db.query(cls).filter(cls.id == history_id).first()
        if history_record:
            for key, value in kwargs.items():
                setattr(history_record, key, value)
            db.commit()
            db.refresh(history_record)
            return history_record
        return None

    @classmethod
    def delete(cls, db: Session, history_id: int):
        history_record = db.query(cls).filter(cls.id == history_id).first()
        if history_record:
            db.delete(history_record)
            db.commit()
            return True
        return False

    @classmethod
    def select_in_period(cls, db: Session, start_date: dt.datetime, end_date: dt.datetime) -> List['AssetHistoryDB']:
        return db.query(cls).filter(cls.created_at >= start_date, cls.created_at <= end_date).all()