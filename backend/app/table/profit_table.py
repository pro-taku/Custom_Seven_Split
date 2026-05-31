from sqlalchemy import Column, DateTime, String, Integer
from app.core.connect import Base

class Profit(Base):
    __tablename__ = "profits"

    updated_at = Column(DateTime)           # 업데이트 시간 (YYYY-MM-DD HH:MM:SS)
    account_number = Column(String(20))     # 계좌 번호
    split_level = Column(Integer)           # 분할 레벨 (1~7)
    stock_code = Column(String(20))         # 종목 코드
    buy_odno = Column(String(20), primary_key=True)  # 매수 주문번호를 기본키로 사용
    sell_odno = Column(String(20), primary_key=True)  # 매도 주문번호를 기본키로 사용
    profit = Column(Integer)                # 실현 손익