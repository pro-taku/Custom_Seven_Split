from sqlalchemy import Column, String, Integer, DateTime, CHAR
from app.core.connect import Base

class Trade(Base):
    __tablename__ = "trades"

    date = Column(DateTime, primary_key=True)
    account_number = Column(String(20), primary_key=True)
    split_level = Column(Integer)
    stock_code = Column(String(20))
    buy_sell = Column(CHAR(1))  # 'B' or 'S'
    order_price = Column(Integer)
    order_quantity = Column(Integer)
    status = Column(CHAR(1))  # 'O', 'F', 'C'
