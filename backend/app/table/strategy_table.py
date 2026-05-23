from sqlalchemy import Column, String, Integer, Float
from app.core.connect import Base

class Strategy(Base):
    __tablename__ = "strategies"

    account_number = Column(String(20), primary_key=True)
    stock_code = Column(String(10), primary_key=True)
    initial_price = Column(Integer)
    buy_rate = Column(Float)
    first_sell_rate = Column(Float)
    sell_rate = Column(Float)
    split_level = Column(Integer)
