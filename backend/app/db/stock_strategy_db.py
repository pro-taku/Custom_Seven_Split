from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import Session

from app.db.session import Base


class StockStrategyDB(Base):
    __tablename__ = "stock_strategy_db"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String, unique=True, nullable=False)  # Changed to unique
    split_level = Column(Integer)
    invested_capital = Column(Integer)
    buy_price = Column(Integer)
    buy_per = Column(Float)
    first_sell_per = Column(Float)
    sell_per = Column(Float)

    def __repr__(self):
        return f"<StockStrategyDB(id={self.id}, stock_code='{self.stock_code}')>"

    @classmethod
    def create(
        cls,
        db: Session,
        stock_code: str,
        split_level: int,
        invested_capital: int,
        buy_price: int,
        buy_per: float,
        first_sell_per: float,
        sell_per: float,
    ):
        new_strategy = cls(
            stock_code=stock_code,
            split_level=split_level,
            invested_capital=invested_capital,
            buy_price=buy_price,
            buy_per=buy_per,
            first_sell_per=first_sell_per,
            sell_per=sell_per,
        )
        db.add(new_strategy)
        db.commit()
        db.refresh(new_strategy)
        return new_strategy

    @classmethod
    def get(cls, db: Session, strategy_id: int):
        return db.query(cls).filter(cls.id == strategy_id).first()

    @classmethod
    def get_by_stock_code(cls, db: Session, stock_code: str):
        return db.query(cls).filter(cls.stock_code == stock_code).first()

    @classmethod
    def get_all(cls, db: Session) -> list["StockStrategyDB"]:
        return db.query(cls).all()

    @classmethod
    def update(cls, db: Session, strategy_id: int, **kwargs):
        strategy = db.query(cls).filter(cls.id == strategy_id).first()
        if strategy:
            for key, value in kwargs.items():
                setattr(strategy, key, value)
            db.commit()
            db.refresh(strategy)
            return strategy
        return None

    @classmethod
    def delete(cls, db: Session, strategy_id: int):
        strategy = db.query(cls).filter(cls.id == strategy_id).first()
        if strategy:
            db.delete(strategy)
            db.commit()
            return True
        return False
