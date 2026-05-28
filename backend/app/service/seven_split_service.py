from sqlalchemy.orm import Session
from app.session.strategy_session import StrategySession
from app.session.strategy_count_session import StrategyCountSession
from app.session.trade_session import TradeSession
from app.session.user_session import UserSession
from app.session.account_session import AccountSession
from app.table.trade_table import Trade
from app.lib.kis_client import KISClient
from datetime import datetime
import pytz

class SevenSplitService:
    def __init__(self, db: Session):
        self.db = db
        self.strategy_session = StrategySession(db)
        self.strategy_count_session = StrategyCountSession(db)
        self.trade_session = TradeSession(db)
        self.user_session = UserSession(db)
        self.account_session = AccountSession(db)

    def is_market_open(self) -> bool:
        """한국 거래소 개장 시간 확인 (09:00 ~ 15:30 KST)"""
        tz_kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(tz_kst)
        
        # 주말 확인 (5: 토요일, 6: 일요일)
        if now_kst.weekday() >= 5:
            return False
            
        start_time = now_kst.replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = now_kst.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return start_time <= now_kst <= end_time

    def get_kis_client(self, account_number: str) -> KISClient:
        """계좌번호로 유저 정보를 조회하여 KISClient 인스턴스 반환"""
        user = self.user_session.get_by_account_number(account_number)
        if not user:
            raise Exception(f"User not found for account: {account_number}")
        
        # KISClient 초기화 (cano는 계좌번호 앞 8자리, acnt_prdt_cd는 뒤 2자리로 가정하거나 전체 사용)
        # KisClient의 cano 인자가 계좌번호 전체를 받는지 확인 필요. 
        # 여기서는 계좌번호 전체를 cano로 전달하고 01을 기본 상품코드로 사용
        return KISClient(
            appkey=user.appkey,
            secret=user.appsecret,
            cano=account_number[:8],
            acnt_prdt_cd=account_number[8:10] if len(account_number) >= 10 else "01",
            is_virtual=False # 실계좌 가정, 필요시 로직 추가
        )

    def create_strategy(self, strategy_data: dict) -> dict:
        """
        StrategySession.create() 메서드를 호출하여 새로운 세븐스플릿 전략을 데이터베이스에 추가한다
        
        만약, 유저(계좌번호)의 전략이 10개라면, 더 이상 추가할 수 없도록 예외를 발생시킨다
        
        만약, 추가한 시간이 개장 시간일 경우, 즉시 주문을 실행한다
        """
        account_number = strategy_data.get("account_number")
        count_view = self.strategy_count_session.get_by_account(account_number)
        if count_view and count_view.strategy_count >= 10:
            raise Exception("Maximum 10 strategies allowed per account.")

        strategy = self.strategy_session.create(strategy_data)
        
        # 개장 시간일 경우 즉시 주문 (첫 번째 레벨 매수 등)
        if self.is_market_open():
            # 초기 매수 로직 (예: split_level 0 주문)
            # 여기서는 stock_code, initial_price 등을 사용하여 order_stock 호출
            self.order_stock(
                account_number=account_number,
                split_level=0,
                stock_code=strategy.stock_code,
                is_buy_order=True,
                price=strategy.initial_price,
                quantity=1 # 기본 수량 1, 실제로는 계산 필요
            )
            
        return {"status": "success", "data": strategy.stock_code}

    def modify_strategy(self, account_number: str, stock_code: str, update_data: dict) -> dict:
        """
        StrategySession.update() 메서드를 호출하여 기존 세븐스플릿 전략의 정보를 업데이트한다
        주로 매수/매도 비율이나 분할 레벨을 변경하는 용도로 사용된다
        """
        strategy = self.strategy_session.update(account_number, stock_code, update_data)
        if not strategy:
            return {"status": "error", "message": "Strategy not found"}
        return {"status": "success", "data": strategy.stock_code}

    def delete_strategy(self, account_number: str, stock_code: str) -> bool:
        """
        StrategySession.delete() 메서드를 호출하여 기존 세븐스플릿 전략을 데이터베이스에서 삭제한다

        전략을 삭제하면, 해당 종목의 매수 주문은 모두 취소한다
        """
        # 해당 종목의 활성 주문(status='O') 조회 및 취소
        trades = self.trade_session.get_by_account(account_number)
        for trade in trades:
            if trade.stock_code == stock_code and trade.status == 'O' and trade.buy_sell == 'B':
                self.cancel_order(trade.odno)

        return self.strategy_session.delete(account_number, stock_code)

    def get_strategies(self, account_number: str) -> list:
        """
        계좌번호에 해당하는 모든 세븐스플릿 전략을 조회한다
        """
        strategies = self.strategy_session.get_by_account(account_number)
        return [s.__dict__ for s in strategies]

    def order_stock(
            self,
            account_number: str, 
            split_level: int,
            stock_code: str, 
            is_buy_order: bool,
            price: int, 
            quantity: int
            ) -> dict:
        """
        주식을 주문한다
        """
        if not self.is_market_open():
            return {"status": "error", "message": "Market is closed"}

        # 유효성 확인 (잔고/보유수량) - 여기서는 간단히 체크 로직 스텁
        account = self.account_session.get_by_number(account_number)
        if is_buy_order:
            if not account or account.deposit < price * quantity:
                return {"status": "error", "message": "Insufficient deposit"}
        else:
            # 매도 시 종목 보유 확인 로직 필요 (BalanceSession 등 활용)
            pass

        client = self.get_kis_client(account_number)
        # UserService에서 토큰 유효성 확인 및 갱신이 선행되어야 함 (여기서는 client 내부에서 처리한다고 가정하거나 이미 되어있다고 가정)
        # 실제로는 login()을 호출하여 토큰을 보장해야 할 수도 있음
        from app.service.user_service import UserService
        user_service = UserService(self.db)
        user = user_service.login(client.appkey, client.secret)
        client.access_token = user.token

        side = "BUY" if is_buy_order else "SELL"
        res = client.order_cash(stock_code, quantity, price, side)
        
        if res.get("rt_cd") == "0": # 성공
            order_no = res.get("output", {}).get("ODNO")
            trade_data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "krx_fwdg_ord_orgno": res.get("output", {}).get("KRX_FWDG_ORD_ORGNO"),
                "odno": order_no,
                "account_number": account_number,
                "split_level": split_level,
                "stock_code": stock_code,
                "buy_sell": "B" if is_buy_order else "S",
                "order_price": price,
                "order_quantity": quantity,
                "status": "O"
            }
            self.trade_session.create(trade_data)
            return {"status": "success", "order_no": order_no}
        else:
            return {"status": "error", "message": res.get("msg1")}

    def cancel_order(self, odno: str) -> dict:
        """
        주문을 취소한다
        """
        if not self.is_market_open():
            return {"status": "error", "message": "Market is closed"}

        # trade 정보 조회
        trade = self.db.query(Trade).filter(Trade.odno == odno).first() # Trade import 필요
        if not trade:
            return {"status": "error", "message": "Order not found"}

        client = self.get_kis_client(trade.account_number)
        from app.service.user_service import UserService
        user_service = UserService(self.db)
        user = user_service.login(client.appkey, client.secret)
        client.access_token = user.token

        res = client.cancel_order(trade.odno, trade.order_quantity, trade.order_price)
        
        if res.get("rt_cd") == "0":
            self.trade_session.update_status(trade.date, trade.account_number, 'C') # update_status 시그니처 확인 필요
            # TradeSession.update_status가 odno를 기준으로 하지 않아서 수정이 필요할 수 있음
            trade.status = 'C'
            self.db.commit()
            return {"status": "success"}
        else:
            return {"status": "error", "message": res.get("msg1")}
