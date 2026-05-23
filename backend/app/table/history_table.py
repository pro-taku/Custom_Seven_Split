from sqlalchemy import Column, String, Integer, DateTime
from app.core.connect import Base

class History(Base):
    __tablename__ = "histories"

    date = Column(DateTime, primary_key=True)
    account_number = Column(String(20), primary_key=True)
    split_level = Column(Integer, primary_key=True)
    market_value = Column(Integer)
    deposit = Column(Integer)
    valuation_gain_loss = Column(Integer)
