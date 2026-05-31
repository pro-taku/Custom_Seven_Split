
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

import pytz

from app.lib.kis_client import KISClient
from app.session.account_session import AccountSession
from app.session.stock_session import StockSession
from app.session.trade_session import TradeSession
from app.session.user_session import UserSession


class StockService:
    def __init__(self, db : Session):
        self.trade_session = TradeSession(db)
        self.user_session = UserSession(db)
        self.account_session = AccountSession(db)
        self.stock_session = StockSession(db)
        self.client = KISClient | None

    def get_kis_client(self, account_number: str) -> None:
        """계좌번호로 유저 정보를 조회하여 KISClient 인스턴스 반환"""
        user = self.user_session.get_by_account_number(account_number)
        if not user:
            raise Exception(f"User not found for account: {account_number}")
        
        self.client = KISClient(
            appkey=user.appkey,
            appsecret=user.appsecret,
            cano=account_number[:8],
            acnt_prdt_cd=account_number[8:10] if len(account_number) >= 10 else "01",
        )
        
    def is_market_open(self) -> bool:
        if not self.client:
            raise Exception("KISClient is not initialized. Call get_kis_client() first.")

        now = datetime.now(pytz.timezone('Asia/Seoul'))
        response = self.client.chk_holiday(now.strftime("%Y%m%d"))
        return response['output'][0]['opnd_yn'] == 'Y'  # 'Y'면 영업일, 'N'이면 휴장일

    def order_stock(self):
        pass

    def cancel_order(self):
        pass
        
    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        종목 정보를 조회한다
        """
        if not self.client:
            raise Exception("KISClient is not initialized. Call get_kis_client() first.")

        stock = self.stock_session.get_by_code(stock_code)
        if stock:
            return {
                "stock_code": stock.stock_code,
                "stock_name": stock.stock_name,
                "stock_logo_url": stock.stock_logo_url,
                "stock_aspr_unit": stock.stock_aspr_unit
            }

        # DB에 없는 경우 KIS API에서 조회하여 DB에 저장
        response = self.client.inquire_price(stock_code)['output']
        new_stock = {
            "stock_code": stock_code,
            "stock_name": response['bstp_kor_isnm'],
            "stock_logo_url": "", # KIS API에서 로고 URL을 제공하지 않는 경우 빈 문자열로 저장하거나 별도의 로고 매핑 로직 필요
            "stock_aspr_unit": response['aspr_unit']
        }
        self.stock_session.create(new_stock)
        return new_stock

    def calculate_price(self, stock_code: str, base_price: int) -> int:
        stock = self.stock_session.get_by_code(stock_code)
        if not stock:
            raise Exception(f"Stock not found for code: {stock_code}")

        n1 = base_price % stock.stock_aspr_unit
        if n1 == 0:
            return base_price
        
        if n1 >= stock.stock_aspr_unit / 2:
            return base_price + (stock.stock_aspr_unit - n1)
        else:
            return base_price - n1

    def get_trades(
        self, 
        account_number: str,
        stock_code: Optional[str] = None,
        status: Optional[str] = None,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        order_by: Optional[str] = None
    ) -> list:
        output = []
        stocks = {}
        trades = self.trade_session.get_by_filter(
            account_number=account_number,
            stock_code=stock_code,
            status=status,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            order_by=order_by
        )

        for trade in trades:
            if trade.stock_code not in stocks:
                stock_info = self.get_stock_info(trade.stock_code)
                stocks[trade.stock_code] = stock_info
            else:
                stock_info = stocks[trade.stock_code]
                
            output.append({
                "created_at": trade.created_at,
                "odno": trade.odno,
                "account_number": trade.account_number,
                "split_level": trade.split_level,
                "stock_code": trade.stock_code,
                "stock_name": stock_info['stock_name'],
                "stock_logo_url": stock_info['stock_logo_url'],
                "buy_sell": trade.buy_sell,
                "order_price": trade.order_price,
                "order_quantity": trade.order_quantity,
                "status": trade.status
            })

        return output