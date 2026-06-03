
from sqlalchemy.orm import Session

from app.session.strategy_count_session import StrategyCountSession
from app.session.strategy_session import StrategySession
from backend.app.service.stock_service import StockService
from backend.app.session.account_session import AccountSession
from backend.app.session.balance_session import BalanceSession
from backend.app.session.profit_session import ProfitSession
from backend.app.session.trade_session import TradeSession

class SevenSplitService:
    def __init__(self, db: Session):
        self.account_session = AccountSession(db)
        self.balance_session = BalanceSession(db)
        self.profit_session = ProfitSession(db)
        self.strategy_session = StrategySession(db)
        self.strategy_count_session = StrategyCountSession(db)
        self.trade_session = TradeSession(db)

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

    def get_strategy_list(self, account_number: str) -> list:
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

    def when_order_executed(self, odno: str):
        trade = self.trade_session.get_by_odno(odno)
        if not trade:
            raise Exception("해당 주문이 존재하지 않습니다.")
        self.trade_session.update_status(odno, 'E') # 주문 상태를 'Executed'로 업데이트

        strategy = self.strategy_session.get(trade.account_number, trade.stock_code)

        # 매수 주문이 체결된 경우
        if trade.buy_sell == 'BUY':
            # 잔고에 매수 정보 추가
            self.balance_session.create({
                "account_number": trade.account_number,
                "stock_code": trade.stock_code,
                "split_level": trade.split_level,
                "price": trade.order_price,
                "quantity": trade.order_quantity,
            })
            # 예수금 차감
            self.account_session.update(
                account_number=trade.account_number,
                update_data={"deposit": -trade.order_price * trade.order_quantity}
            )
            # 전략 업데이트
            self.strategy_session.update(
                trade.account_number,
                trade.stock_code,
                {"split_level": trade.split_level}
            )
            # 개장시간이라면, 주문 요청
            if self.stock_service.is_market_open():
                # N+1 계좌에 매수 주문 요청 (단, N은 7보다 작은 경우에만)
                if trade.split_level < 7:
                    buy_price = self.stock_service.calculate_price(
                        trade.stock_code,
                        int(trade.order_price * (1 - strategy.buy_rate))
                    )
                    self.stock_service.order_stock()
                # N 계좌에 매도 주문 요청
                sell_price = 0
                if trade.split_level == 1:
                    sell_price = self.stock_service.calculate_price(
                        trade.stock_code,
                        int(trade.order_price * (1 + strategy.first_sell_rate))
                    )
                else:
                    sell_price = self.stock_service.calculate_price(
                        trade.stock_code,
                        int(trade.order_price * (1 + strategy.sell_rate))
                    )
                self.stock_service.order_stock()

        # 매도 주문이 체결된 경우
        elif trade.buy_sell == 'SELL':
            # 잔고에서 매도 정보 제거 및 손익 계산
            balance = self.balance_session.get(
                account_number=trade.account_number,
                stock_code=trade.stock_code,
                split_level=trade.split_level
            )
            if balance:
                profit_amount = (trade.order_price - balance.price) * balance.quantity
                self.profit_session.create({
                    "account_number": trade.account_number,
                    "stock_code": trade.stock_code,
                    "split_level": trade.split_level,
                    "profit": profit_amount,
                })
                self.balance_session.delete(
                    account_number=trade.account_number,
                    stock_code=trade.stock_code,
                    split_level=trade.split_level
                )
            # 예수금 증가
            self.account_session.update(
                account_number=trade.account_number,
                update_data={"deposit": trade.order_price * trade.order_quantity}
            )
            # 전략 업데이트
            self.strategy_session.update(
                trade.account_number,
                trade.stock_code,
                {"split_level": trade.split_level - 1}
            )
            # 개장시간이라면, 주문 요청
            if self.stock_service.is_market_open():
                # N-1 계좌에 매도 주문 요청 (단, N은 1보다 큰 경우에만)
                if trade.split_level > 1:
                    sell_price = 0
                    if trade.split_level == 2:
                        sell_price = self.stock_service.calculate_price(
                            trade.stock_code,
                            int(trade.order_price * (1 + strategy.first_sell_rate))
                        )
                    else:
                        sell_price = self.stock_service.calculate_price(
                            trade.stock_code,
                            int(trade.order_price * (1 + strategy.sell_rate))
                        )
                    self.stock_service.order_stock()
                # N 계좌에 매수 주문 요청
                buy_price = self.stock_service.calculate_price(
                    trade.stock_code,
                    int(trade.order_price * (1 - strategy.buy_rate))
                )
                self.stock_service.order_stock()
                # N+1 계좌에 매수 주문 취소 요청
                if trade.split_level < 7:
                    self.stock_service.cancel_order()

        # 예외 처리
        else:
            raise Exception("잘못된 주문 유형입니다.")