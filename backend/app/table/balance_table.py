from sqlalchemy import Column, String, Integer
from app.core.connect import Base

class Balance(Base):
    __tablename__ = "balances"

    account_number = Column(String(20), primary_key=True)
    split_level = Column(Integer, primary_key=True)
    stock_code = Column(String(10))
    price = Column(Integer)
    quantity = Column(Integer)
