from sqlalchemy import Column, String, DateTime
from app.core.connect import Base

class User(Base):
    __tablename__ = "users"

    appkey = Column(String(100), primary_key=True)
    appsecret = Column(String(100), primary_key=True)
    token = Column(String(100))
    websocket = Column(String(100))
    expiration = Column(String(100))
    account_number = Column(String(20))
