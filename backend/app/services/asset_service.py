import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.account_db import AccountDB
from app.db.asset_history_db import AssetHistoryDB
from app.db.cash_flow_db import CashFlow
from app.db.trade_check_db import TradeCheckDB
from app.lib.kis.client import KISClient

logger = logging.getLogger(__name__)

# Global environment variable, set from main.py
GLOBAL_ENV: str = "V"


class AssetService:
    def __init__(self, db: Session):
        """지금 부족한 것 : KIS 관련 함수"""
        self.db = db
        self.kis_client = KISClient(env=GLOBAL_ENV)  # KISClient 인스턴스 초기화

    # 종목 매수 기록
    def record_buy_stock(
        self,
        split_level: int,
        stock_code: str,
        price: int,
        count: int,
        trade_id: int,
    ):
        """
        account_db에 stock_code가 (split_level)번 계좌에 추가됐음을 기록

        cash_flow_db에 매수금만큼 차감했음을 기록

        trade_check_db에 이번 매수 내용을 추가
        """
        AccountDB.create(self.db, split_level, stock_code, price, count)

        amount = price * count
        current_deposit = CashFlow.select_in_period(
            self.db,
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).date(),
            datetime.now(),
        )[-1].deposit
        self.record_cash_flow(
            flow_type="매수",
            amount=-amount,
            current_deposit=current_deposit,
        )
        TradeCheckDB.update(self.db, trade_id=trade_id, status=1)

    # 종목 매도 기록
    def record_sell_stock(
        self,
        split_level: int,
        stock_code: str,
        price: int,
        count: int,
        trade_id: int,
    ):
        """
        account_db에 stock_code가 (split_level)번 계좌에 삭제됐음을 기록

        cash_flow_db에 매수금만큼 수급됐음을 기록

        trade_check_db의 Row를 status=1로 변경
        """
        AccountDB.delete(self.db, split_level, stock_code)

        amount = price * count
        current_deposit = CashFlow.select_in_period(
            self.db,
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).date(),
            datetime.now(),
        )[-1].deposit
        self.record_cash_flow(
            flow_type="매도",
            amount=amount,
            current_deposit=current_deposit,
        )

        TradeCheckDB.update(self.db, trade_id, status=1)

    # cash flow 기록
    # 입출금, 배당금, 매매금 등을 기록하기 위한 함수
    def record_cash_flow(self, flow_type: str, amount: int, current_deposit: int = 0):
        """
        cash_flow_db에 자금 변동이 있음을 기록

        ㄴtype 속성은 ('입금', '출금', '배당금', '이자', '매수', '매도')가 들어감
        """
        CashFlow.create(
            self.db,
            deposit=current_deposit,
            flow_type=flow_type,
            amount=amount,
        )

    # 자산추이 기록
    async def asset_snapshot(self):
        """
        asset_history_db에 오늘 날짜로 항목들 기록
        """

        total_invested = 0
        total_value = 0

        for i in range(1, 8):
            accounts = AccountDB.select_virtual_account(self.db, i)
            for acc in accounts:
                if self.kis_client:
                    try:
                        current_price = await self.kis_client.inquire_price(
                            acc.stock_code,
                        )
                    except Exception as e:
                        logger.error(f"Failed to fetch price for {acc.stock_code}: {e}")
                        current_price = acc.price
                else:
                    current_price = acc.price

                total_invested += acc.price * acc.count
                total_value += current_price * acc.count

        stock_pnl = total_value - total_invested

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now()

        flows = CashFlow.select_in_period(self.db, today_start, today_end)

        deposit = flows[-1].deposit if flows else 0

        net_cash_flow = sum(f.amount for f in flows if f.type in ["입금", "출금"])
        dividend = sum(f.amount for f in flows if f.type == "배당금")
        interest = sum(f.amount for f in flows if f.type == "이자")

        total_pnl = stock_pnl + dividend + interest
        net_asset_change = total_pnl + net_cash_flow

        AssetHistoryDB.create(
            self.db,
            invested_capital=total_invested,
            total_asset_value=total_value,
            cash_balance=deposit,
            net_cash_flow=net_cash_flow,
            dividend=dividend,
            interest=interest,
            stock_pnl=stock_pnl,
            total_pnl=total_pnl,
            net_asset_change=net_asset_change,
        )

    # 전체 자산 조회
    async def get_total_asset(self):
        """Return { 예수금, 투입자본, 평가금액, 손익, stock_dict }"""
        stock_dict = {}
        total_invested = 0
        total_value = 0
        total_pnl = 0

        for i in range(1, 8):
            accounts = AccountDB.select_virtual_account(self.db, i)
            for acc in accounts:
                if acc.stock_code not in stock_dict:
                    stock_dict[acc.stock_code] = {
                        "투입자본": 0,
                        "평가금액": 0,
                        "수량": 0,
                    }

                if self.kis_client:
                    try:
                        current_price = await self.kis_client.inquire_price(
                            acc.stock_code,
                        )
                    except Exception:
                        current_price = acc.price
                else:
                    current_price = acc.price

                stock_dict[acc.stock_code]["투입자본"] += acc.price * acc.count
                stock_dict[acc.stock_code]["평가금액"] += current_price * acc.count
                stock_dict[acc.stock_code]["수량"] += acc.count

        all_flows = CashFlow.get_all(self.db)
        deposit = all_flows[-1].deposit if all_flows else 0

        for _code, data in stock_dict.items():
            if data["수량"] > 0:
                data["평균단가"] = data["투입자본"] / data["수량"]
            else:
                data["평균단가"] = 0
            data["손익"] = data["평가금액"] - data["투입자본"]
            total_invested += data["투입자본"]
            total_value += data["평가금액"]
            total_pnl += data["손익"]

        return {
            "예수금": deposit,
            "투입자본": total_invested,
            "평가금액": total_value,
            "손익": total_pnl,
            "stock_dict": stock_dict,
        }

    # x번 가상계좌 자산 조회
    async def get_virtual_account_asset(self, split_level: int):
        """Return { 투입자본, 평가금액, 손익, stock_dict }"""
        stock_dict = {}
        total_invested = 0
        total_value = 0
        total_pnl = 0

        accounts = AccountDB.select_virtual_account(self.db, split_level)

        for acc in accounts:
            if acc.stock_code not in stock_dict:
                stock_dict[acc.stock_code] = {"투입자본": 0, "평가금액": 0, "수량": 0}

            if self.kis_client:
                try:
                    current_price = await self.kis_client.inquire_price(
                        acc.stock_code,
                    )
                except Exception:
                    current_price = acc.price
            else:
                current_price = acc.price

            stock_dict[acc.stock_code]["투입자본"] += acc.price * acc.count
            stock_dict[acc.stock_code]["평가금액"] += current_price * acc.count
            stock_dict[acc.stock_code]["손익"] = (
                stock_dict[acc.stock_code]["평가금액"]
                - stock_dict[acc.stock_code]["투입자본"]
            )

            total_invested += stock_dict[acc.stock_code]["투입자본"]
            total_value += stock_dict[acc.stock_code]["평가금액"]
            total_pnl += stock_dict[acc.stock_code]["손익"]

        return {
            "투입자본": total_invested,
            "평가금액": total_value,
            "손익": total_pnl,
            "stock_dict": stock_dict,
        }

    # 현금 흐름 조회
    def get_cash_flow(self, start_date: datetime, end_date: datetime):
        """cash_flow_db에서 기간 안에 들어있는 Row를 조회 & 반환"""
        return CashFlow.select_in_period(self.db, start_date, end_date)

    # 자산추이 조회
    def get_asset_history(self, start_date: datetime, end_date: datetime):
        """asset_history_db에서 기간 안에 있는 Row를 조회 & 반환"""
        return AssetHistoryDB.select_in_period(self.db, start_date, end_date)
