from sqlalchemy.orm import Session
from app.table.stock_table import Stock
from typing import Optional, List

class StockSession:
    def __init__(self, db: Session):
        self.db = db

    def create(self, stock_data: dict) -> Stock:
        db_stock = Stock(**stock_data)
        self.db.add(db_stock)
        self.db.commit()
        self.db.refresh(db_stock)
        return db_stock

    def delete(self, stock_code: str) -> bool:
        db_stock = self.get_by_code(stock_code)
        if db_stock:
            self.db.delete(db_stock)
            self.db.commit()
            return True
        return False

    def get_by_code(self, stock_code: str) -> Optional[Stock]:
        return self.db.query(Stock).filter(Stock.stock_code == stock_code).first()

    def get_all(self) -> List[Stock]:
        return self.db.query(Stock).all()
