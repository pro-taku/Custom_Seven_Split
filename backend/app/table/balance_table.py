from sqlalchemy import Column, String, Integer
from app.core.connect import Base

class Balance(Base):
    __tablename__ = "balances"

    account_number = Column(String(20), primary_key=True)   # 계좌 번호
    split_level = Column(Integer, primary_key=True)         # 분할 레벨 (1~7)
    stock_code = Column(String(10), primary_key=True) # 종목 코드
    price = Column(Integer)         # 매수 가격
    quantity = Column(Integer)      # 매수 수량
