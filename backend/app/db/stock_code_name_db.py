from sqlalchemy import Column, String
from sqlalchemy.orm import Session

from app.db.session import Base


class StockCodeNameDB(Base):
    __tablename__ = "stock_code_name_db"

    stock_code = Column(String, primary_key=True)
    stock_name = Column(String, unique=True, nullable=False)

    def __repr__(self):
        return f"<StockCodeNameDB(stock_code='{self.stock_code}', stock_name='{self.stock_name}')>"

    @classmethod
    def create(cls, db: Session, stock_code: str, stock_name: str):
        new_entry = cls(stock_code=stock_code, stock_name=stock_name)
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return new_entry

    @classmethod
    def get(cls, db: Session, stock_code: str):
        return db.query(cls).filter(cls.stock_code == stock_code).first()

    @classmethod
    def get_stock_name(cls, db: Session, stock_code: str) -> str | None:
        entry = db.query(cls).filter(cls.stock_code == stock_code).first()
        return entry.stock_name if entry else None

    @classmethod
    def get_all(cls, db: Session) -> list["StockCodeNameDB"]:
        return db.query(cls).all()

    @classmethod
    def update(cls, db: Session, stock_code: str, new_stock_name: str):
        entry = db.query(cls).filter(cls.stock_code == stock_code).first()
        if entry:
            entry.stock_name = new_stock_name
            db.commit()
            db.refresh(entry)
            return entry
        return None

    @classmethod
    def delete(cls, db: Session, stock_code: str):
        entry = db.query(cls).filter(cls.stock_code == stock_code).first()
        if entry:
            db.delete(entry)
            db.commit()
            return True
        return False
