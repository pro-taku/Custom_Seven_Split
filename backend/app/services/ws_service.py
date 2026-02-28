import asyncio
import logging

import websockets
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.stock_strategy_db import StockStrategyDB
from app.lib.kis.client import KISWsClient
from app.lib.kis.model import RealtimeExecutionResponse, RealtimeQuoteResponse
from app.services.css_trade_service import CSSTradeService

logger = logging.getLogger(__name__)


class WSService:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(WSService, cls).__new__(cls)
        return cls._instance

    def initialize(self, env: str = "V"):
        if self._initialized:  # type: ignore
            return
        self.kis_ws_client = KISWsClient(env=env)
        self.ws_url = f"{self.kis_ws_client.ws_domain}/tryitout/H0STCNI0"
        self.is_running = False
        self.websocket = None
        self.subscribed_quotes = set()
        self.latest_prices = {}  # {stock_code: price}
        self._initialized = True  # type: ignore

    async def start(self):
        if not self._initialized:  # type: ignore
            logger.error("WSService not initialized. Call initialize() first.")
            return

        if self.is_running:
            logger.info("WebSocket Service is already running.")
            return

        self.is_running = True
        logger.info("Starting WebSocket Service...")

        # 발급된 접속키가 없으면 새로 발급
        await self.kis_ws_client.load_websocket_approval_key()

        while self.is_running:
            try:
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=60,
                ) as websocket:
                    self.websocket = websocket
                    logger.info(f"Connected to KIS WebSocket: {self.ws_url}")

                    # 1. 내 계좌에 대한 체결통보 구독
                    execution_req = self.kis_ws_client.subscribe_realtime_execution(
                        self.kis_ws_client.account_num,
                    )
                    await websocket.send(execution_req)
                    logger.info(
                        f"Subscribed to realtime execution for {self.kis_ws_client.account_num}",
                    )

                    # 2. 감시 중인 종목들에 대한 현재가 구독 (DB에서 읽어옴)
                    db: Session = SessionLocal()
                    try:
                        strategies = StockStrategyDB.get_all(db)
                        for strategy in strategies:
                            stock_code = strategy.stock_code
                            if stock_code not in self.subscribed_quotes:
                                quote_req = self.kis_ws_client.subscribe_realtime_quote(
                                    stock_code,
                                )
                                await websocket.send(quote_req)
                                self.subscribed_quotes.add(stock_code)
                                logger.info(
                                    f"Subscribed to realtime quote for {stock_code}",
                                )
                    finally:
                        db.close()

                    # 메시지 수신 루프
                    while self.is_running:
                        message = await websocket.recv()
                        await self.handle_message(message)

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(
                    f"WebSocket Connection Closed: {e}. Reconnecting in 5 seconds...",
                )
                self.websocket = None
                self.subscribed_quotes.clear()
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket Error: {e}. Reconnecting in 5 seconds...")
                self.websocket = None
                self.subscribed_quotes.clear()
                await asyncio.sleep(5)

    async def stop(self):
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket Service stopped.")

    async def subscribe_new_quote(self, stock_code: str):
        """새로운 종목 감시 추가 시 호출"""
        if (
            self.websocket
            and self.is_running
            and stock_code not in self.subscribed_quotes
        ):
            quote_req = self.kis_ws_client.subscribe_realtime_quote(stock_code)
            try:
                await self.websocket.send(quote_req)
                self.subscribed_quotes.add(stock_code)
                logger.info(f"Subscribed to new realtime quote for {stock_code}")
            except Exception as e:
                logger.error(f"Failed to subscribe to new quote for {stock_code}: {e}")

    async def unsubscribe_quote(self, stock_code: str):
        """종목 감시 삭제 시 호출"""
        if self.websocket and self.is_running and stock_code in self.subscribed_quotes:
            quote_req = self.kis_ws_client.unsubscribe_realtime_data(
                tr_id=self.kis_ws_client.TR.TR_KS_RT_PRICE_R.value,
                tr_key=stock_code,
                tr_type="2",
            )
            try:
                await self.websocket.send(quote_req)
                self.subscribed_quotes.remove(stock_code)
                logger.info(f"Unsubscribed from realtime quote for {stock_code}")
            except Exception as e:
                logger.error(f"Failed to unsubscribe from quote for {stock_code}: {e}")

    async def handle_message(self, message: str):
        header, parsed_response = self.kis_ws_client._process_websocket_message(message)

        if not parsed_response:
            # Control message (PING/PONG or subscription confirmation)
            if header.get("tr_id") == "PINGPONG":
                logger.debug("Received PING, sending PONG")
                # ping is usually handled automatically, but if needed we can handle here
            return

        if isinstance(parsed_response, RealtimeExecutionResponse):
            # 체결통보 처리
            trade_type_raw = parsed_response.output.trade_type
            if trade_type_raw == "1":
                trade_type = "SELL"
            elif trade_type_raw == "2":
                trade_type = "BUY"
            else:
                return  # 정정/취소 통보 등은 일단 무시

            # 체결 수량이 0보다 큰 경우만 처리
            ccld_qty = parsed_response.output.ccld_qty
            if ccld_qty > 0:
                stock_code = parsed_response.output.iscd
                ccld_prc = parsed_response.output.ccld_prc

                logger.info(
                    f"[WS] Execution Notification: {trade_type} {ccld_qty} of {stock_code} @ {ccld_prc}",
                )

                # DB 업데이트
                db: Session = SessionLocal()
                try:
                    css_trade_service = CSSTradeService(db)
                    await css_trade_service.check_trade_result(
                        stock_code=stock_code,
                        trade_type=trade_type,
                        execution_price=ccld_prc,
                        execution_qty=ccld_qty,
                    )
                except Exception as e:
                    logger.error(f"Error handling trade result for {stock_code}: {e}")
                finally:
                    db.close()

        elif isinstance(parsed_response, RealtimeQuoteResponse):
            # 실시간 호가(현재가) 업데이트
            stock_code = parsed_response.tr_key
            current_price = parsed_response.output.stck_prpr
            self.latest_prices[stock_code] = current_price
            logger.debug(f"[WS] Realtime Quote: {stock_code} - {current_price}")

    def get_latest_price(self, stock_code: str) -> int | None:
        """메모리에 저장된 최신 현재가를 반환"""
        return self.latest_prices.get(stock_code)


# 싱글톤 인스턴스로 사용할 수 있도록 객체 생성
ws_service_instance = WSService()
