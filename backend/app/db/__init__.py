# This file makes the 'db' directory a Python package.
from .account_db import AccountDB
from .asset_history_db import AssetHistoryDB
from .cash_flow_db import CashFlow
from .session import Base, engine
from .stock_strategy_db import StockStrategyDB
from .trade_db import TradeDB


def create_all_tables():
    Base.metadata.create_all(bind=engine)
