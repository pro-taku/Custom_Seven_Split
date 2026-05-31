from sqlalchemy import Column, String, Integer, Float

from app.core.connect import Base

class Account(Base):
    __tablename__ = "accounts"

    account_number = Column(String(20), primary_key=True)
    principal = Column(Integer)     # 투자 원금
    deposit = Column(Integer)       # 예수금
    long_ratio = Column(Float)      # 장기 투자 비중
