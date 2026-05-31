
from sqlalchemy.orm import Session

from app.session.strategy_count_session import StrategyCountSession
from app.session.strategy_session import StrategySession
from backend.app.service.stock_service import StockService
from backend.app.session.account_session import AccountSession
from backend.app.session.balance_session import BalanceSession
from backend.app.session.profit_session import ProfitSession

class SevenSplitService:
    def __init__(self, db: Session):
        self.account_session = AccountSession(db)
        self.balance_session = BalanceSession(db)
        self.strategy_session = StrategySession(db)
        self.strategy_count_session = StrategyCountSession(db)
        self.profit_session = ProfitSession(db)

        self.stock_service = StockService(db)

    def create_strategy(
        self,
        account_number: str,
        stock_code: str,
        initial_price: int,
        buy_rate: float,
        first_sell_rate: float,
        sell_rate: float,
    ):
        if self.strategy_count_session.get_by_account(account_number).count >= 10:
            raise Exception("최대 10개의 전략만 생성할 수 있습니다.")
        
        if self.strategy_session.get(account_number, stock_code):
            raise Exception("이미 해당 종목에 대한 전략이 존재합니다.")

        self.strategy_session.create({
            "account_number": account_number,
            "stock_code": stock_code,
            "initial_price": initial_price,
            "buy_rate": buy_rate,
            "first_sell_rate": first_sell_rate,
            "sell_rate": sell_rate,
            "split_level": 1,
        })

        self.stock_service.get_kis_client(account_number)
        if self.stock_service.is_market_open():
            account = self.account_session.get_by_number(account_number)
            investment = account.principal * account.long_ratio * 0.05  # 1회 투자금액 계산 (예: 전체 원금의 5%)

            self.stock_service.order_stock(
                # account_number=account_number,
                # stock_code=stock_code,
                # is_buy_order=True,
                # price=initial_price,
                # quantity=investment // initial_price
            )

    def modify_strategy(self, account_number: str, stock_code: str, strategy_data: dict):
        strategy = self.strategy_session.get(account_number, stock_code)
        if not strategy:
            raise Exception("해당 전략이 존재하지 않습니다.")
        
        self.strategy_session.update(account_number, stock_code, strategy_data)

    def delete_strategy(self, account_number: str, stock_code: str):
        strategy = self.strategy_session.get(account_number, stock_code)
        if not strategy:
            raise Exception("해당 전략이 존재하지 않습니다.")
        
        self.strategy_session.delete(account_number, stock_code)

    def get_strategies(self, account_number: str) -> list:
        strategies = self.strategy_session.get_by_account(account_number)
        result = []
        for strategy in strategies:
            stock_info = self.stock_service.get_stock_info(strategy.stock_code)
            result.append({
                "stock_name": stock_info["stock_name"],
                "stock_code": stock_info["stock_code"],
                "split_level": strategy.split_level,
                "initial_price": strategy.initial_price,
            })
        return result

    def get_strategy(self, account_number: str, stock_code: str) -> dict:
        strategy = self.strategy_session.get(account_number, stock_code)
        if not strategy:
             raise Exception("해당 전략이 존재하지 않습니다.")
        
        stock_info = self.stock_service.get_stock_info(stock_code)
        
        balances = self.balance_session.get_by_account_and_stock(account_number, stock_code)
        trade_history = [{"level" : i} for i in range(1, 8)]
        for balance in balances:
            trade_history[balance.split_level - 1]["price"] = balance.price
            trade_history[balance.split_level - 1]["quantity"] = balance.quantity

        profit = self.profit_session.get_sum_profit_by_account_and_stock(account_number, stock_code)

        return {
            "stock_name" : stock_info["stock_name"],
            "stock_code" : stock_info["stock_code"],
            "split_level" : strategy.split_level,
            "initial_price" : strategy.initial_price,
            "buy_rate" : strategy.buy_rate,
            "first_sell_rate" : strategy.first_sell_rate,
            "sell_rate" : strategy.sell_rate,
            "priority" : None,
            "trade_history" : trade_history,
            "profit" : profit,
        }