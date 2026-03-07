import datetime as dt
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import Session

from app.db.session import Base


class TradeDB(Base):
    __tablename__ = "trade_db"

    trade_id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=dt.datetime.now)
    stock_code = Column(String)
    trade_type = Column(String)  # BUY, SELL
    split_level = Column(
        Integer,
    )  # 분할 레벨 (1~MAX_SPLIT_LEVEL, 0 이면 가상계좌에 미포함)
    price = Column(Integer)
    count = Column(Integer)
    status = Column(Integer)  # 0=대기중, 1=체결, 2=취소

    def __repr__(self):
        return f"<TradeDB(id={self.trade_id}, stock_code='{self.stock_code}', trade_type='{self.trade_type}')>"

    @classmethod
    def create(
        cls,
        trade_id: str,
        db: Session,
        stock_code: str,
        trade_type: str,
        split_level: int,
        price: int,
        count: int,
        status: int,
    ):
        new_trade = cls(
            trade_id=trade_id,
            stock_code=stock_code,
            trade_type=trade_type,
            split_level=split_level,
            price=price,
            count=count,
            status=status,
        )
        db.add(new_trade)
        db.commit()
        db.refresh(new_trade)
        return new_trade

    @classmethod
    def get(cls, db: Session, trade_id: str):
        return db.query(cls).filter(cls.trade_id == trade_id).first()

    @classmethod
    def get_all(cls, db: Session) -> list["TradeDB"]:
        return db.query(cls).all()

    @classmethod
    def update(cls, db: Session, trade_id: str, **kwargs):
        trade_record = db.query(cls).filter(cls.trade_id == trade_id).first()
        if trade_record:
            for key, value in kwargs.items():
                setattr(trade_record, key, value)
            db.commit()
            db.refresh(trade_record)
            return trade_record
        return None

    @classmethod
    def delete(cls, db: Session, trade_id: str):
        trade_record = db.query(cls).filter(cls.trade_id == trade_id).first()
        if trade_record:
            db.delete(trade_record)
            db.commit()
            return True
        return False

    @classmethod
    def select(
        cls,
        db: Session,
        start_date: Optional[dt.date] = None,
        end_date: Optional[dt.date] = None,
        stock_code: Optional[str] = None,
        trade_type: Optional[str] = None,
        split_level: Optional[int] = None,
        status: Optional[int] = None,
    ):
        query = db.query(cls)
        if start_date is not None:
            query = query.filter(cls.created_at >= start_date)
        if end_date is not None:
            query = query.filter(cls.created_at <= end_date)
        if stock_code is not None:
            query = query.filter(cls.stock_code == stock_code)
        if trade_type is not None:
            query = query.filter(cls.trade_type == trade_type)
        if split_level is not None:
            query = query.filter(cls.split_level == split_level)
        if status is not None:
            query = query.filter(cls.status == status)
        return query.order_by(cls.created_at.desc()).all()
