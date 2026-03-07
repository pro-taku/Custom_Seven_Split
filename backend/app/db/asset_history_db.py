import datetime as dt

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import Session

from app.db.session import Base


class AssetHistoryDB(Base):
    __tablename__ = "asset_history_db"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=dt.datetime.now)
    invested_capital = Column(Integer)
    stock_valutation = Column(Integer)
    deposit = Column(Integer)
    net_cash_flow = Column(Integer)
    dividend = Column(Integer)
    interest = Column(Integer)
    stock_profit_loss = Column(Integer)
    total_profit_loss = Column(Integer)
    fund_change = Column(Integer)

    def __repr__(self):
        return f"<AssetHistoryDB(id={self.id}, created_at={self.created_at}, stock_valutation={self.stock_valutation})>"

    @classmethod
    def create(
        cls,
        db: Session,
        invested_capital: int,
        stock_valutation: int,
        deposit: int,
        net_cash_flow: int,
        dividend: int,
        interest: int,
        stock_profit_loss: int,
        total_profit_loss: int,
        fund_change: int,
    ):
        new_history = cls(
            invested_capital=invested_capital,
            stock_valutation=stock_valutation,
            deposit=deposit,
            net_cash_flow=net_cash_flow,
            dividend=dividend,
            interest=interest,
            stock_profit_loss=stock_profit_loss,
            total_profit_loss=total_profit_loss,
            fund_change=fund_change,
        )
        db.add(new_history)
        db.commit()
        db.refresh(new_history)
        return new_history

    @classmethod
    def get(cls, db: Session, history_id: int):
        return db.query(cls).filter(cls.id == history_id).first()

    @classmethod
    def get_all(cls, db: Session) -> list["AssetHistoryDB"]:
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
    def select(
        cls,
        db: Session,
        start_date: dt.datetime,
        end_date: dt.datetime,
    ) -> list["AssetHistoryDB"]:
        return (
            db.query(cls)
            .filter(cls.created_at >= start_date, cls.created_at <= end_date)
            .all()
        )
