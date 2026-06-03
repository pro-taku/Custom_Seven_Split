from sqlalchemy import Column, DateTime, String, Integer
from app.core.connect import Base

class Profit(Base):
    __tablename__ = "profits"

    updated_at = Column(DateTime)           # 업데이트 시간 (YYYY-MM-DD HH:MM:SS)
    account_number = Column(String(20))     # 계좌 번호
    split_level = Column(Integer)           # 분할 레벨 (1~7)
    stock_code = Column(String(20))         # 종목 코드
    profit = Column(Integer)                # 실현 손익