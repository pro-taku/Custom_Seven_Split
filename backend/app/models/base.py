from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
)
from sqlalchemy.orm import relationship
import datetime

from app.db.session import Base


class SystemSetting(Base):
    __tablename__ = "system_setting"
    account_num = Column(String, primary_key=True, index=True)
    app_key = Column(String, nullable=False)
    app_secret = Column(String, nullable=False)
    is_virtual = Column(Boolean, default=True)
    default_gap_ratio = Column(Float, default=0.03)
    default_target_return = Column(Float, default=0.05)


class StockStrategy(Base):
    __tablename__ = "stock_strategy"
    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String, unique=True, index=True, nullable=False)
    stock_name = Column(String, nullable=False)
    status = Column(String, default="RUNNING")
    gap_ratio = Column(Float, nullable=False)
    target_return = Column(Float, nullable=False)
    invest_per_split = Column(Integer, nullable=False)
    max_split = Column(Integer, default=7)

    balances = relationship("VirtualAccount", back_populates="strategy")
    histories = relationship("TradeHistory", back_populates="strategy")


class VirtualAccount(Base):
    __tablename__ = "virtual_account"
    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String, ForeignKey("stock_strategy.stock_code"), nullable=False)
    split_number = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)

    strategy = relationship("StockStrategy", back_populates="balances")


class TradeHistory(Base):
    __tablename__ = "trade_history"
    id = Column(Integer, primary_key=True, index=True)
    trade_time = Column(DateTime, default=datetime.datetime.now)
    stock_code = Column(String, ForeignKey("stock_strategy.stock_code"), nullable=False)
    trade_type = Column(String, nullable=False)  # BUY or SELL
    split_number = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    realized_profit = Column(Integer, nullable=True)

    strategy = relationship("StockStrategy", back_populates="histories")


# class CashFlowBaseModel(Base): # Renamed to avoid overlap or just removed. Let's comment it out instead.
#     __tablename__ = "cash_flow"
#     id = Column(Integer, primary_key=True, index=True)
#     created_at = Column(DateTime, default=datetime.datetime.now)
#     flow_type = Column(String, nullable=False)  # DEPOSIT, WITHDRAW, DIVIDEND
#     amount = Column(Integer, nullable=False)
#     memo = Column(String, nullable=True)


class DailySummary(Base):
    __tablename__ = "daily_summary"
    date = Column(Date, primary_key=True, index=True, default=datetime.date.today)
    total_asset = Column(Integer, nullable=False)
    total_invested = Column(Integer, nullable=False)
    daily_profit = Column(Integer, nullable=False)
