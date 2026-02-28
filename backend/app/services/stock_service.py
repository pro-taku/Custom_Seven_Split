from typing import Any

from sqlalchemy.orm import Session

from app.lib.kis.client import KISClient

# Global environment variable, set from main.py
GLOBAL_ENV: str = "V"


class StockService:
    def __init__(self, db: Session):
        self.db = db
        self.kis_client = KISClient(env=GLOBAL_ENV)  # KISClient 인스턴스 초기화

    # 주식 현재가 조회
    async def get_current_price(self, stock_code: str) -> int | None:
        """KIS에서 stock_code의 현재가 반환"""
        if self.kis_client:
            return await self.kis_client.inquire_price(stock_code)
        return None

    # ▼ 확인 필요. 해당 클래스에서 WS을 사용할 수 있는지는 불명하기 때문에
    # 주식 현재가 조회 (실시간)
    # async def get_current_price_rt(
    #     self,
    #     stock_code: str,
    # ) -> AsyncGenerator[dict[str, Any], None]:
    #     """* 웹소켓을 사용
    #     KIST에서 stock_code의 현재가를 실시간 반환
    #     """
    #     if self.kis_client:
    #         async for data in self.kis_client.get_rt_current_price(stock_code):
    #             yield data

    # 주식 주문 요청
    async def order(
        self,
        stock_code: str,
        quantity: int,
        price: int,
        side: str = "BUY",
        order_division: str = "00",
    ) -> dict[str, Any]:
        """KIS로 stock_code의 주식을 현금 주문 요청"""
        if self.kis_client:
            return await self.kis_client.order_cash(
                stock_code,
                quantity,
                price,
                side,
                order_division,
            )
        return {"error": "KIS client not initialized"}

    # 주식 주문 정정
    async def modify_order(
        self,
        original_order_no: str,
        stock_code: str,
        new_quantity: int,
        new_price: int,
        order_division: str = "00",
    ) -> dict[str, Any]:
        """KIS로 특정 거래의 내용을 변경"""
        if self.kis_client:
            return await self.kis_client.order_rvsecncl(
                original_order_no,
                stock_code,
                new_quantity,
                new_price,
                order_division,
            )
        return {"error": "KIS client not initialized"}

    # 주식 주문 취소
    async def cancel_order(
        self,
        original_order_no: str,
        order_division: str = "00",
    ) -> dict[str, Any]:
        """KIS로 특정 거래를 취소"""
        if self.kis_client:
            return await self.kis_client.order_rvsecncl(
                original_order_no,
                order_division=order_division,
            )
        return {"error": "KIS client not initialized"}

    # 주식 주문 조회
    async def get_orders(
        self,
        order_date: str,
        product_code: str = "",
    ) -> dict[str, Any]:
        """KIS로 내가 넣은 주문 조회 (정정/취소 가능 주문 조회 API 사용)"""
        if self.kis_client:
            return await self.kis_client.inquire_psbl_rvsecncl(
                order_date,
                product_code,
            )
        return {"error": "KIS client not initialized"}

    # 주식 정보 조회
    async def get_stock_info(self, stock_code: str) -> dict[str, Any]:
        """KIS로 stock_code의 정보 조회.
        Note: KIS client에 직접적인 'info' 함수가 없으면 현재가를 대신 사용하거나 확장이 필요함.
        """
        if self.kis_client:
            price = await self.kis_client.inquire_price(stock_code)
            return {"stock_code": stock_code, "current_price": price}
        return {"error": "KIS client not initialized"}
