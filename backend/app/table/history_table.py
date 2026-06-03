from sqlalchemy import Column, String, Integer, DateTime
from app.core.connect import Base

class History(Base):
    __tablename__ = "histories"

    date = Column(DateTime, primary_key=True)   # 기록 날짜 (YYYY-MM-DD)
    account_number = Column(String(20), primary_key=True)   # 계좌 번호
    deposit = Column(Integer)                   # 예수금
    investment = Column(Integer)                # 투자 원금
    market_value = Column(Integer)              # 평가 금액
    valuation_gain_loss = Column(Integer)       # 평가 손익 (평가 금액 - 투자 금액)
