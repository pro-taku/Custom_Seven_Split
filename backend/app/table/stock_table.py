from sqlalchemy import Column, String, Integer
from app.core.connect import Base

class Stock(Base):
    __tablename__ = "stocks"

    stock_code = Column(String(10), primary_key=True)   # 종목 코드
    stock_name = Column(String(100))        # 종목명
    stock_logo_url = Column(String(200))    # 종목 로고 URL
    stock_aspr_unit = Column(Integer)       # 호가 단위 (예: 100, 500, 1000 등)
