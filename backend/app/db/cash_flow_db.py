import datetime as dt

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import Session

from app.db.session import Base


class CashFlow(Base):
    __tablename__ = "cash_flow"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=dt.datetime.now)
    deposit = Column(Integer)
    type = Column(String)  # input, output, buy, sell, dividend, interest
    amount = Column(Integer)

    def __repr__(self):
        return f"<CashFlow(id={self.id}, type='{self.type}', amount={self.amount})>"

    @classmethod
    def create(cls, db: Session, deposit: int, flow_type: str, amount: int):
        new_cash_flow = cls(deposit=deposit, type=flow_type, amount=amount)
        db.add(new_cash_flow)
        db.commit()
        db.refresh(new_cash_flow)
        return new_cash_flow

    @classmethod
    def get(cls, db: Session, cash_flow_id: int):
        return db.query(cls).filter(cls.id == cash_flow_id).first()

    @classmethod
    def get_all(cls, db: Session) -> list["CashFlow"]:
        return db.query(cls).all()

    @classmethod
    def update(cls, db: Session, cash_flow_id: int, **kwargs):
        cash_flow_record = db.query(cls).filter(cls.id == cash_flow_id).first()
        if cash_flow_record:
            for key, value in kwargs.items():
                setattr(cash_flow_record, key, value)
            db.commit()
            db.refresh(cash_flow_record)
            return cash_flow_record
        return None

    @classmethod
    def delete(cls, db: Session, cash_flow_id: int):
        cash_flow_record = db.query(cls).filter(cls.id == cash_flow_id).first()
        if cash_flow_record:
            db.delete(cash_flow_record)
            db.commit()
            return True
        return False

    @classmethod
    def select_in_period(
        cls,
        db: Session,
        start_date: dt.datetime,
        end_date: dt.datetime,
    ) -> list["CashFlow"]:
        return (
            db.query(cls)
            .filter(cls.created_at >= start_date, cls.created_at <= end_date)
            .all()
        )

    @classmethod
    def select_by_type(cls, db: Session, flow_type: str) -> list["CashFlow"]:
        return db.query(cls).filter(cls.type == flow_type).all()
