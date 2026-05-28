from sqlalchemy import Column, String, Integer
from app.core.connect import Base

class Stock(Base):
    __tablename__ = "stocks"

    stock_code = Column(String(10), primary_key=True)
    stock_name = Column(String(100))
    stock_logo_url = Column(String(200))
    stock_aspr_unit = Column(Integer)
