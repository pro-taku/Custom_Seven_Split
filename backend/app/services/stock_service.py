from datetime import datetime

from backend.app.db.trade_db import TradeDB
from backend.app.lib.kis.model import (
    InquirePsblOrderResponse,
    OrderRvsecnclResponse,
)
from sqlalchemy.orm import Session

# Global environment variable, set from main.py
from app.core.config import GLOBAL_ENV, IS_HOLIDAY, TradeStatus, TradeType
from app.lib.kis.client import KISClient


class StockService:
    def __init__(self, db: Session):
        self.db = db
        self.kis_client = KISClient(env=GLOBAL_ENV)  # KISClient 인스턴스 초기화

    # 휴장일 여부 조회
    async def is_today_holiday(self):
        global IS_HOLIDAY
        today = datetime.now().date()
        IS_HOLIDAY = await self.kis_client.chk_holiday(today)

    # 주식 주문 요청
    async def order(
        self,
        stock_code: str,
        quantity: int,
        price: int,
        trade_type: TradeType,
        trade_id: str = None,
        split_level: int = 0,
    ):
        # 지금 장이 닫혀있다면 에러 raise
        if IS_HOLIDAY:
            raise Exception("오늘은 휴장일입니다.")

        if trade_type == TradeType.BUY:
            # 매수 가능한지 확인
            response: InquirePsblOrderResponse = (
                await self.kis_client.inquire_psbl_order(
                    pdno=stock_code,
                    ord_unpr=price,
                )
            )
            if response.rt_cd != "0":
                raise ValueError(f"매수 불가능: {response.msg1}")
            if response.output.nrcvb_buy_qty < quantity:
                raise ValueError(
                    f"매수 불가능: 주문 수량이 매수 가능 수량({response.output.nrcvb_buy_qty})보다 많습니다.",
                )
        elif trade_type != TradeType.SELL:
            raise ValueError("Invalid trade type. Must be 'BUY' or 'SELL'")

        # KIS 주문 요청
        response = await self.kis_client.order_cash(
            trade_type=trade_type,
            pdno=stock_code,
            ord_qty=quantity,
            ord_unpr=price,
        )
        if response.rt_cd != "0":
            raise ValueError(f"주문 실패: {response.msg1}")

        # 주문 내역 DB에 기록
        if not trade_id:
            TradeDB.create(
                self.db,
                trade_id=response.output.ord_no,  # KIS에서 반환된 주문 번호를 trade_id로 사용
                stock_code=stock_code,
                trade_type=trade_type.value,
                split_level=split_level,
                price=price,
                count=quantity,
                status=TradeStatus.PENDING.value,  # 주문 요청 시점에서는 아직 체결되지 않았으므로 대기중(0)으로 기록
            )

    # 주식 주문 정정
    async def modify_order(
        self,
        trade_id: str,
        quantity: int = None,
        price: int = None,
        split_level: int = None,
    ):
        # 수량, 가격 둘 다 없으면 에러 raise
        if quantity is None and price is None and split_level is None:
            raise ValueError(
                "수량, 가격, 또는 분할 레벨 중 하나는 반드시 입력해야 합니다.",
            )

        # 지금 장이 닫혀있다면 에러 raise
        if IS_HOLIDAY:
            raise Exception("오늘은 휴장일입니다.")

        # 주문 정정이 가능한지 확인 (나중에)

        # 주문 정정 요청
        response: OrderRvsecnclResponse = await self.kis_client.order_rvsecncl(
            rvse_cncl_dvsn_cd="01",  # 01: 정정
            orgn_odno=trade_id,
            ord_qty=quantity,
            ord_unpr=price,
        )
        if response.rt_cd != "0":
            raise ValueError(f"주문 정정 실패: {response.msg1}")

        # 주문 내역 DB 업데이트
        trade = TradeDB.get_by_trade_id(self.db, trade_id)
        if trade is None:
            raise ValueError(f"주문 내역을 찾을 수 없습니다: trade_id={trade_id}")
        TradeDB.update(
            self.db,
            trade_id=trade_id,
            status=TradeStatus.CANCELED.value,
        )
        TradeDB.create(
            self.db,
            trade_id=response.output.odno,
            stock_code=trade.stock_code,
            trade_type=trade.trade_type,
            split_level=split_level if split_level is not None else trade.split_level,
            price=price if price is not None else trade.price,
            count=quantity if quantity is not None else trade.count,
            status=TradeStatus.PENDING.value,
        )

    # 주식 주문 취소
    async def cancel_order(
        self,
        trade_id: str,
    ):
        # 지금 장이 닫혀있다면 에러 raise
        if IS_HOLIDAY:
            raise Exception("오늘은 휴장일입니다.")

        # 주문 취소가 가능한지 확인 (나중에)

        # 주문 취소 요청
        response: OrderRvsecnclResponse = await self.kis_client.order_rvsecncl(
            rvse_cncl_dvsn_cd="02",  # 02: 취소
            orgn_odno=trade_id,
        )
        if response.rt_cd != "0":
            raise ValueError(f"주문 취소 실패: {response.msg1}")

        # 주문 내역 DB 업데이트
        trade = TradeDB.get_by_trade_id(self.db, trade_id)
        if trade is None:
            raise ValueError(f"주문 내역을 찾을 수 없습니다: trade_id={trade_id}")
        TradeDB.update(
            self.db,
            trade_id=trade_id,
            status=TradeStatus.CANCELED.value,
        )

    # 주식 주문 조회
    async def get_orders(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        stock_code: str = None,
        trade_type: TradeType = None,
        split_level: int = None,
        status: TradeStatus = None,
    ):
        if start_date is None:
            start_date = datetime.now().date()
        if end_date is None:
            end_date = datetime.now().date() - datetime.timedelta(days=7)
        return TradeDB.select(
            self.db,
            start_date=start_date,
            end_date=end_date,
            stock_code=stock_code,
            trade_type=trade_type.value if trade_type else None,
            split_level=split_level,
            status=status.value if status else None,
        )

    # 주식 현재가 조회
    async def get_current_price(self, stock_code: str):
        response = await self.kis_client.inquire_price(stock_code=stock_code)
        if response.rt_cd != "0":
            raise ValueError(f"현재가 조회 실패: {response.msg1}")
        return response.model_dump()["output"]["stck_prpr"]

    # 회사명 조회
    async def get_stock_name(self, stock_code: str):
        response = await self.kis_client.search_stock_info(stock_code=stock_code)
        if response.rt_cd != "0":
            raise ValueError(f"회사명 조회 실패: {response.msg1}")
        return response.model_dump()["output"]["prdt_name"]

    # 호가단위 조회
    async def get_price_unit(self, stock_code: str):
        response = await self.kis_client.inquire_price(stock_code=stock_code)
        if response.rt_cd != "0":
            raise ValueError(f"호가단위 조회 실패: {response.msg1}")
        return response.model_dump()["output"]["aspr_unit"]

    # TODO: 복잡한 관계로 생략!
    # # 주식 주문 정정 가능 여부 조회
    # async def _check_modify_order(
    #     self,
    #     trade_id: str,
    #     trade_type: TradeType,
    # ) -> bool:
    #     ctx_area_fk100 = ""
    #     ctx_area_nk100 = ""
    #     while True:
    #         response: InquirePsblRvsecnclResponse = (
    #             await self.kis_client.inquire_psbl_rvsecncl(
    #                 inqr_dvsn_1="0",  # 0: 주문
    #                 inqr_dvsn_2="0",  # 0: 매수+매도
    #                 ctx_area_fk100=ctx_area_fk100,
    #                 ctx_area_nk100=ctx_area_nk100,
    #             )
    #         )
    #         if response.rt_cd != "0":
    #             raise ValueError(f"주문 정정 가능 여부 조회 실패: {response.msg1}")
    #         for item in response.output:
    #             if item.odno == trade_id and item.rvse_cncl_dvsn_name == "???":
    #                 return True
    #             if not response.output.has_next:
    #                 return False
