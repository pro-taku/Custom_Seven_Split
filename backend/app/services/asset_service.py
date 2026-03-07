from datetime import datetime

from backend.app.db.trade_db import TradeDB
from backend.app.services.stock_service import StockService
from fastapi.logger import logger
from sqlalchemy.orm import Session

from app.core.config import GLOBAL_ENV, CashFlowType
from app.db.account_db import AccountDB
from app.db.asset_history_db import AssetHistoryDB
from app.db.cash_flow_db import CashFlow
from app.lib.kis.client import KISClient


class AssetService:
    def __init__(self, db: Session):
        self.db = db
        self.kis_client = KISClient(env=GLOBAL_ENV)

    # 종목 매수 기록
    async def record_buy_stock(
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
        stock_service = StockService(self.db)
        try:
            stock_name = await stock_service.get_stock_name(stock_code)
        except Exception as e:
            logger.error(f"Failed to fetch stock name for {stock_code}: {e}")
            stock_name = "Unknown"

        AccountDB.create(
            self.db,
            split_level,
            stock_code,
            stock_name,
            price,
            count,
        )

        amount = price * count
        # TODO : current_deposit 계산해서 넣어주기
        # current_deposit = CashFlow.select_in_period(
        #     self.db,
        #     datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).date(),
        #     datetime.now(),
        # )[-1].deposit
        self.record_cash_flow(
            flow_type="buy",
            amount=-amount,
            # current_deposit=current_deposit,
            current_deposit=0,
        )
        TradeDB.update(self.db, trade_id=trade_id, status=1)

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
        # TODO : current_deposit 계산해서 넣어주기
        # current_deposit = CashFlow.select_in_period(
        #     self.db,
        #     datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).date(),
        #     datetime.now(),
        # )[-1].deposit
        self.record_cash_flow(
            flow_type="매도",
            amount=amount,
            # current_deposit=current_deposit,
            current_deposit=0,
        )

        TradeDB.update(self.db, trade_id, status=1)

    # cash flow 기록
    # 입출금, 배당금, 매매금 등을 기록하기 위한 함수
    def record_cash_flow(
        self,
        flow_type: CashFlowType,
        amount: int,
        current_deposit: int = 0,
    ):
        """
        cash_flow_db에 자금 변동이 있음을 기록

        ㄴtype 속성은 (input, output, buy, sell, dividend, interest)가 들어감
        """
        if flow_type not in CashFlowType:
            raise ValueError(
                f"Invalid flow_type. Must be one of: {list(CashFlowType)}",
            )

        CashFlow.create(
            self.db,
            deposit=current_deposit,
            flow_type=flow_type.value,
            amount=amount,
        )

    # cash flow 수정
    def modify_cash_flow(
        self,
        cash_flow_id: int,
        flow_type: CashFlowType = None,
        amount: int = None,
        current_deposit: int = None,
    ):
        if CashFlow.get(self.db, cash_flow_id) is None:
            raise ValueError(f"CashFlow with id {cash_flow_id} does not exist.")

        CashFlow.update(
            self.db,
            cash_flow_id,
            type=flow_type.value if flow_type else None,
            amount=amount,
            deposit=current_deposit,
        )

    # cash flow 삭제
    def delete_cash_flow(self, cash_flow_id: int):
        """
        cash_flow_db에서 특정 Row를 삭제
        """
        return CashFlow.delete(self.db, cash_flow_id)

    # 현금 흐름 조회
    def get_cash_flow(
        self,
        start_date: datetime,
        end_date: datetime,
        type: CashFlowType = None,
    ):
        """cash_flow_db에서 기간 안에 들어있는 Row를 조회 & 반환"""
        if type and type not in CashFlowType:
            raise ValueError(
                f"Invalid flow_type. Must be one of: {list(CashFlowType)}",
            )
        return CashFlow.select(
            self.db,
            start_date,
            end_date,
            type=type.value if type else None,
        )

    # 실물계좌 자산 조회
    # TODO : KIS에 있는 진짜 계좌로 연결하기
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
                        "이름": acc.stock_name,
                        "투입자본": 0,
                        "평가금액": 0,
                        "수량": 0,
                    }

                with StockService(self.db) as stock_service:
                    try:
                        current_price = await stock_service.get_current_price(
                            acc.stock_code,
                        )
                    except Exception as e:
                        logger.error(f"Failed to fetch price for {acc.stock_code}: {e}")
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

    # 가상계좌 자산 조회
    async def get_virtual_account_asset(self, split_level: int):
        """Return { 투입자본, 평가금액, 손익, stock_dict }"""
        stock_dict = {}
        total_invested = 0
        total_value = 0
        total_pnl = 0

        accounts = AccountDB.select_virtual_account(self.db, split_level)

        for acc in accounts:
            if acc.stock_code not in stock_dict:
                stock_dict[acc.stock_code] = {
                    "이름": acc.stock_name,
                    "투입자본": 0,
                    "평가금액": 0,
                    "수량": 0,
                }

            with StockService(self.db) as stock_service:
                try:
                    current_price = await stock_service.get_current_price(
                        acc.stock_code,
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch price for {acc.stock_code}: {e}")
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

    # 자산추이 추가
    async def add_asset_history(self):
        invested_capital = 0
        stock_valutation = 0

        for i in range(1, 8):
            accounts = AccountDB.select(self.db, split_level=i)
            for acc in accounts:
                with StockService(self.db) as stock_service:
                    try:
                        current_price = await stock_service.get_current_price(
                            acc.stock_code,
                        )
                    except Exception as e:
                        logger.error(f"Failed to fetch price for {acc.stock_code}: {e}")
                        current_price = acc.price

                invested_capital += acc.price * acc.count
                stock_valutation += current_price * acc.count

        stock_profit_loss = stock_valutation - invested_capital

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now()

        flows = CashFlow.select(
            self.db,
            start_date=today_start,
            end_date=today_end,
        )

        deposit = flows[-1].deposit if flows else 0

        net_cash_flow = sum(
            f.amount
            for f in flows
            if f.type in [CashFlowType.input.value, CashFlowType.output.value]
        )
        dividend = sum(f.amount for f in flows if f.type == CashFlowType.dividend.value)
        interest = sum(f.amount for f in flows if f.type == CashFlowType.interest.value)

        total_profit_loss = stock_profit_loss + dividend + interest
        fund_change = total_profit_loss + net_cash_flow

        AssetHistoryDB.create(
            self.db,
            invested_capital=invested_capital,
            stock_valutation=stock_valutation,
            deposit=deposit,
            net_cash_flow=net_cash_flow,
            dividend=dividend,
            interest=interest,
            stock_profit_loss=stock_profit_loss,
            total_profit_loss=total_profit_loss,
            fund_change=fund_change,
        )

    # 자산추이 수정
    def modify_asset_history(
        self,
        history_id: int,
        invested_capital: int = None,
        stock_valutation: int = None,
        deposit: int = None,
        net_cash_flow: int = None,
        dividend: int = None,
        interest: int = None,
        stock_profit_loss: int = None,
        total_profit_loss: int = None,
        fund_change: int = None,
    ):
        if (
            invested_capital is None
            and stock_valutation is None
            and deposit is None
            and net_cash_flow is None
            and dividend is None
            and interest is None
            and stock_profit_loss is None
            and total_profit_loss is None
            and fund_change is None
        ):
            raise ValueError("At least one field must be provided for update.")

        if AssetHistoryDB.get(self.db, history_id) is None:
            raise ValueError(f"AssetHistory with id {history_id} does not exist.")

        AssetHistoryDB.update(
            self.db,
            history_id,
            invested_capital=invested_capital,
            stock_valutation=stock_valutation,
            deposit=deposit,
            net_cash_flow=net_cash_flow,
            dividend=dividend,
            interest=interest,
            stock_profit_loss=stock_profit_loss,
            total_profit_loss=total_profit_loss,
            fund_change=fund_change,
        )

    # 자산추이 삭제
    def delete_asset_history(self, history_id: int):
        """
        asset_history_db에서 특정 Row를 삭제
        """
        return AssetHistoryDB.delete(self.db, history_id)

    # 자산추이 조회
    def get_asset_history(self, start_date: datetime, end_date: datetime):
        """asset_history_db에서 기간 안에 있는 Row를 조회 & 반환"""
        return AssetHistoryDB.select(self.db, start_date, end_date)
