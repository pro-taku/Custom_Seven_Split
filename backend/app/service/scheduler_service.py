import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

from app.lib.kis_client import KISClient, TRID
from app.service.ws_service import KISWebSocketManager
from app.service.seven_split_service import SevenSplitService
from app.service.stock_service import StockService
from app.session.user_session import UserSession
from app.session.account_session import AccountSession
from app.session.trade_session import TradeSession
from backend.app.session.balance_session import BalanceSession
from backend.app.session.history_session import HistorySession

class SchedulerService:
    def __init__(self, db: Session):
        self.db = db
        self.seven_split_service = SevenSplitService(db)
        self.trade_service = StockService(db)
        self.account_session = AccountSession(db)
        self.balance_session = BalanceSession(db)
        self.history_session = HistorySession(db)
        self.user_session = UserSession(db)
        self.trade_session = TradeSession(db)

    def update_monthly_principal(self):
        """
        매월 1일 00:00 - 원금 업데이트
        모든 계좌의 원금을 최신 정보로 업데이트합니다.
        """
        # 모든 사용자 조회
        users = self.user_session.get_all()
        
        for user in users:
            # 계좌번호에서 앞 8자리와 뒤 2자리 추출
            cano, acnt_prdt_cd = user.account_number.split('-')
            
            # KISClient 인스턴스 생성
            client = KISClient(
                appkey=user.appkey,
                appsecret=user.appsecret,
                cano=cano,
                acnt_prdt_cd=acnt_prdt_cd
            )

            # 접큰 토큰 발급
            client.get_access_token()

            # 주식 잔고 조회
            data = client.inquire_balance()
            deposit = int(data["output2"]["dnca_tot_amt"]) # 예수금
            scts_evlu_amt = int(data["output2"]["scts_evlu_amt"]) # 평가금액
            principal = deposit + scts_evlu_amt

            # DB 업데이트
            self.account_session.update(
                account_number=user.account_number,
                update_data={
                    "principal": principal,
                    "deposit": deposit,
                    "investment": scts_evlu_amt,
                }
            )

        print(f"[{datetime.now()}] Monthly principal update executed.")

    def request_daily_orders(self):
        """
        매 개장일 08:40 - 주문 요청
        개장 전 모든 전략을 점검하고 필요한 매수/매도 주문을 요청합니다.
        """
        users = self.user_session.get_all()
        ws_manager = KISWebSocketManager()

        # 휴장일 체크
        test_client = KISClient(
            appkey=users[0].appkey,
            appsecret=users[0].appsecret,
            cano=users[0].account_number.split('-')[0]
        )
        test_client.get_access_token()
        if test_client.chk_holiday(datetime.now().strftime("%Y%m%d"))['output'][0]['opnd_yn'] == 'N':
            print(f"[{datetime.now()}] Market is closed. Skipping daily order requests.")
            return
        
        for user in users:
            cano, acnt_prdt_cd = user.account_number.split('-')
            client = KISClient(appkey=user.appkey, appsecret=user.appsecret, cano=cano, acnt_prdt_cd=acnt_prdt_cd)
            client.get_access_token()

            # 대기 주문 처리
            trades = self.trade_session.get_unexecuted_trades(user.account_number)
            for trade in trades:
                client.order_cash(symbol=trade.stock_code, qty=trade.order_quantity, price=trade.order_price, side=trade.buy_sell)
                self.trade_session.update_status(odno=trade.odno, status='C')
            
            # 비동기 구독 실행
            asyncio.run_coroutine_threadsafe(
                ws_manager.subscribe(
                    client,
                    TRID.WS_EXECUTION.get_id(),
                    user.hts_id,
                    self._handle_execution_notice
                ),
                asyncio.get_event_loop()
            )

        print(f"[{datetime.now()}] Daily pre-market order requests executed and WS subscriptions requested.")

    def update_daily_asset_trend(self):
        """
        매 개장일 16:00 - 자산추이 업데이트
        장 마감 후 모든 계좌의 자산 현황을 History 테이블에 기록합니다.
        """
        
        users = self.user_session.get_all()

        client = KISClient(
            appkey=users[0].appkey,
            appsecret=users[0].appsecret,
            cano=users[0].account_number.split('-')[0],
            acnt_prdt_cd=users[0].account_number.split('-')[1]
        )
        client.get_access_token()

        if client.chk_holiday(datetime.now().strftime("%Y%m%d"))['output'][0]['opnd_yn'] == 'N':
            print(f"[{datetime.now()}] Market is closed. Skipping daily order requests.")
            return
        
        for user in users:
            account = self.account_session.get_by_number(user.account_number)
            balance = self.balance_session.get_by_account(user.account_number)
            investment = self.balance_session.get_investment_by_account(user.account_number)

            client = KISClient(
                appkey=user.appkey,
                appsecret=user.appsecret,
                cano=account.account_number.split('-')[0],
                acnt_prdt_cd=account.account_number.split('-')[1]
            )
            client.get_access_token()

            market_value = 0
            for b in balance:
                stock_info = client.inquire_price(b.stock_code)['output']
                market_value += int(stock_info[0]['stck_prpr']) * b.quantity

            self.history_session.create({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "account_number": user.account_number,
                "market_value": market_value,
                "deposit": account.deposit,
                "investment": investment,
                "valuation_gain_loss": market_value - investment
            })

            # 실시간체결통보 구독 해지 (웹소켓)
            ws_manager = KISWebSocketManager()
            asyncio.run_coroutine_threadsafe(
                ws_manager.unsubscribe(client, TRID.WS_EXECUTION.get_id(), user.hts_id),
                asyncio.get_event_loop()
            )

        print(f"[{datetime.now()}] Daily post-market asset trend update executed.")

    def _handle_execution_notice(self, message: str):
        """웹소켓 체결 통보 메시지 처리 핸들러 (스레드에서 실행됨)"""
        try:
            parts = message.split('|')
            if len(parts) > 3 and parts[1] == TRID.WS_EXECUTION.get_id():
                # KIS 명세에 따라 데이터 파싱 후 odno 추출
                # 여기서는 예시로 로깅만 수행
                print(f"Execution Notice: {message}")
                # odno = parse_odno(parts[3])
                # if odno:
                #     self.seven_split_service.when_order_executed(odno)
        except Exception as e:
            print(f"Error in WS handler: {e}")