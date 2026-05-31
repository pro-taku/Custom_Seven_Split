from datetime import datetime

from sqlalchemy.orm import Session

from app.service.stock_service import StockService
from app.session.balance_session import BalanceSession
from app.session.history_session import HistorySession

class AssetService:
    def __init__(self, db: Session):
        self.balance_session = BalanceSession(db)
        self.stock_service = StockService(db)
        self.history_session = HistorySession(db)
    
    def get_virtual_accounts(self, account_number: str):
        balances = self.balance_session.get_by_account(account_number)
        investments = self.balance_session.get_investment_by_account(account_number)
        client = self.stock_service.get_kis_client(account_number)
        stocks = {}

        output = [{"level" : i} for i in range(1, 8)]

        for investment in investments:
            output[investment.split_level - 1]['investment'] = investment.investment

        for balance in balances:
            if balance.stock_code not in stocks:
                info = self.stock_service.get_stock_info(client, balance.stock_code)
                stocks[balance.stock_code] = {
                    "stock_name": info['stock_name'],
                    "stock_logo_url": info['stock_logo_url'],
                    "stock_aspr_unit": info['stock_aspr_unit']
                }
            
            output[balance.split_level - 1]["details"] = {
                "stock_code": balance.stock_code,
                "stock_name": stocks[balance.stock_code]['stock_name'],
                "stock_logo_url": stocks[balance.stock_code]['stock_logo_url'],
                "stock_aspr_unit": stocks[balance.stock_code]['stock_aspr_unit'],
                "quantity": balance.quantity,
                "price": balance.price
            }
        
        return output
    
    def get_history(
        self, 
        account_number: str,
        start_date: str | None = None,
        end_date: str | None = None
    ):
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        return self.history_session.get_by_filter(account_number, start_datetime, end_datetime)

    def add_asset(
        self,
        account_number: str,
        split_level: int,
        stock_code: str,
        price: int,
        quantity: int
    ):
        self.balance_session.create({
            "account_number": account_number,
            "split_level": split_level,
            "stock_code": stock_code,
            "price": price,
            "quantity": quantity
        })

    def remove_asset(
        self,
        account_number: str,
        split_level: int,
        stock_code: str,
    ):
        self.balance_session.delete(account_number, split_level, stock_code)