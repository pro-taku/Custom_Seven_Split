from sqlalchemy import Column, String, Integer, DateTime, CHAR
from app.core.connect import Base

class Trade(Base):
    __tablename__ = "trades"

    date = Column(String(10))  # 'YYYY-MM-DD'
    krx_fwdg_ord_orgno = Column(String(20))  # 주문번호 (KIS에서 반환되는 고유 주문번호)
    odno = Column(String(20), primary_key=True)  # 주문번호 (세븐스플릿 전략에서 사용하는 고유 주문번호)
    account_number = Column(String(20))
    split_level = Column(Integer)
    stock_code = Column(String(20))
    buy_sell = Column(CHAR(1))  # 'B' or 'S'
    order_price = Column(Integer)
    order_quantity = Column(Integer)
    status = Column(CHAR(1))  # 'O', 'F', 'C'
