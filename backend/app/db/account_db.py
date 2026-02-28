from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session

from app.db.session import Base


class AccountDB(Base):
    __tablename__ = "account_db"

    split_level = Column(Integer, primary_key=True)
    stock_code = Column(String, primary_key=True)
    price = Column(Integer)
    count = Column(Integer)

    def __repr__(self):
        return f"<AccountDB(split_level={self.split_level}, stock_code='{self.stock_code}', price={self.price}, count={self.count})>"

    @classmethod
    def create(
        cls,
        db: Session,
        split_level: int,
        stock_code: str,
        price: int,
        count: int,
    ):
        new_account = cls(
            split_level=split_level,
            stock_code=stock_code,
            price=price,
            count=count,
        )
        db.add(new_account)
        db.commit()
        db.refresh(new_account)
        return new_account

    @classmethod
    def get(cls, db: Session, split_level: int, stock_code: str):
        return (
            db.query(cls)
            .filter(cls.split_level == split_level, cls.stock_code == stock_code)
            .first()
        )

    @classmethod
    def get_all(cls, db: Session) -> list["AccountDB"]:
        return db.query(cls).all()

    @classmethod
    def update(
        cls,
        db: Session,
        split_level: int,
        stock_code: str,
        new_price: int | None = None,
        new_count: int | None = None,
    ):
        account = (
            db.query(cls)
            .filter(cls.split_level == split_level, cls.stock_code == stock_code)
            .first()
        )
        if account:
            if new_price is not None:
                account.price = new_price
            if new_count is not None:
                account.count = new_count
            db.commit()
            db.refresh(account)
            return account
        return None

    @classmethod
    def delete(cls, db: Session, split_level: int, stock_code: str):
        account = (
            db.query(cls)
            .filter(cls.split_level == split_level, cls.stock_code == stock_code)
            .first()
        )
        if account:
            db.delete(account)
            db.commit()
            return True
        return False

    @classmethod
    def select_virtual_account(cls, db: Session, split_level: int) -> list["AccountDB"]:
        return db.query(cls).filter(cls.split_level == split_level).all()
