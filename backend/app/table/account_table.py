from sqlalchemy import Column, String, Integer, Float
from app.core.connect import Base

class Account(Base):
    __tablename__ = "accounts"

    account_number = Column(String(20), primary_key=True)
    principal = Column(Integer)
    deposit = Column(Integer)
    investment = Column(Integer)
    market_value = Column(Integer)
    long_ratio = Column(Float)
