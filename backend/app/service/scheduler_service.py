from datetime import datetime
from sqlalchemy.orm import Session


from app.lib.kis_client import KISClient
from app.service.seven_split_service import SevenSplitService
from app.service.stock_service import StockService
from app.session.user_session import UserSession
from app.session.account_session import AccountSession
from app.session.trade_session import TradeSession

class SchedulerService:
    def __init__(self, db: Session):
        self.db = db
        self.seven_split_service = SevenSplitService(db)
        self.trade_service = StockService(db)
        self.account_session = AccountSession(db)
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

        client = KISClient(
            appkey=users[0].appkey,
            appsecret=users[0].appsecret,
            cano=users[0].account_number.split('-')[0],
            acnt_prdt_cd=users[0].account_number.split('-')[1]
        )
        client.get_access_token()

        if not KISClient.is_market_open(client):
            print(f"[{datetime.now()}] Market is closed. Skipping daily order requests.")
            return
        
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

            # DB에서 대기 중인 주문 조회
            trades = self.trade_session.get_unexecuted_trades(user.account_number)

            for trade in trades:
                # KIS API로 주문 요청
                client.order_cash(
                    symbol=trade.stock_code,
                    qty=trade.order_quantity,
                    price=trade.order_price,
                    side="BUY" if trade.buy_sell == 'B' else "SELL"
                )
                # 주문 요청 후 상태 업데이트
                self.trade_session.update_status(
                    odno=trade.odno,
                    status='C' # Executed
                )

        print(f"[{datetime.now()}] Daily pre-market order requests executed.")

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

        if not KISClient.is_market_open(client):
            print(f"[{datetime.now()}] Market is closed. Skipping daily order requests.")
            return
        
        for user in users:
            """
            history에 필요한 정보
            1. 예수금
            2. 투자원금
            3. 평가금액
            """

        print(f"[{datetime.now()}] Daily post-market asset trend update executed.")