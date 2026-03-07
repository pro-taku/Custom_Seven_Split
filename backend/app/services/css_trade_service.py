from datetime import datetime

from backend.app.db.trade_db import TradeDB
from backend.app.services.stock_service import StockService
from fastapi.logger import logger
from sqlalchemy.orm import Session

# Global environment variable, set from main.py
from app.core.config import GLOBAL_ENV, TradeStatus, TradeType
from app.db.stock_strategy_db import StockStrategyDB
from app.lib.kis.client import KISClient


class CSSTradeService:
    def __init__(self, db: Session):
        self.db = db
        self.kis_client = KISClient(env=GLOBAL_ENV)  # KISClient 인스턴스 초기화

    # 종목 감시 전략 생성
    async def create_strategy(
        self,
        stock_code: str,
        invested_capital: int,
        buy_price: int,
        buy_per: float = 0.97,
        first_sell_per: float = 1.1,
        sell_per: float = 1.05,
    ):
        # 종목명 조회
        stock_service = StockService(self.db)
        try:
            stock_name = await stock_service.get_stock_name(stock_code)
        except ValueError:
            # TODO : 오류 처리
            raise ValueError(f"Could not fetch stock name for {stock_code}")

        # 종목 감시 전략 DB에 저장
        strategy = StockStrategyDB.create(
            self.db,
            stock_code=stock_code,
            stock_name=stock_name,
            split_level=1,
            invested_capital=invested_capital,
            buy_price=buy_price,
            buy_per=buy_per,
            first_sell_per=first_sell_per,
            sell_per=sell_per,
        )

        # 장이 열려있다면 매수 주문 시도
        is_market_closed = await self.kis_client.chk_holiday(
            date=datetime.now().strftime("%Y%m%d"),
        )
        if not is_market_closed:
            # 호가단위에 맞게 가격 조정
            buy_price = await self._adjust_price_to_unit(stock_code, buy_price)

            # 투자금액과 조정된 가격을 기반으로 주문 수량 계산
            quantity = invested_capital // buy_price
            if quantity > 0:
                try:
                    await stock_service.order(
                        stock_code=stock_code,
                        quantity=quantity,
                        price=buy_price,
                        trade_type=TradeType.BUY,
                    )
                except Exception as e:
                    logger.error(f"Failed to place order for {stock_code}: {e}")

        return strategy

    # 종목 감시 전략 수정
    def change_strategy(
        self,
        stock_code: str,
        buy_price: int | None = None,
        buy_per: float | None = None,
        first_sell_per: float | None = None,
        sell_per: float | None = None,
    ):
        if not any([buy_price, buy_per, first_sell_per, sell_per]):
            raise ValueError("At least one parameter must be provided for update.")

        strategy = StockStrategyDB.get_by_stock_code(self.db, stock_code)
        if not strategy:
            raise ValueError(f"Strategy not found for stock code: {stock_code}")

        update_kwargs = {}
        if buy_price is not None:
            update_kwargs["buy_price"] = buy_price
        if buy_per is not None:
            update_kwargs["buy_per"] = buy_per
        if first_sell_per is not None:
            update_kwargs["first_sell_per"] = first_sell_per
        if sell_per is not None:
            update_kwargs["sell_per"] = sell_per

        if update_kwargs:
            StockStrategyDB.update(self.db, strategy.id, **update_kwargs)
            return StockStrategyDB.get(self.db, strategy.id)
        return strategy

    # 종목 감시 전략 삭제
    def delete_strategy(self, stock_code: str):
        """stock_strategy_db에서 stock_code로 Row 찾기, 해당 Row 삭제"""
        strategy = StockStrategyDB.get_by_stock_code(self.db, stock_code)
        if strategy:
            return StockStrategyDB.delete(self.db, strategy.id)
        return False

    # 종목 감시 전략 조회
    def get_strategy(self, stock_code: str = None):
        if stock_code:
            strategy = StockStrategyDB.get(self.db, stock_code)
            if strategy:
                return strategy
            raise ValueError(f"Strategy not found for stock code: {stock_code}")
        return StockStrategyDB.get_all(self.db)

    # TODO : 다음에 여기부터 확인!!!!
    # 실시간체결여부 웹소켓을 수신했을 시, 동작하는 메시지 핸들러
    async def handle_order_execution_rt(self, message: str):
        # 메시지 파싱
        # TODO: WebSocket 부분에 메서드 추가

        # 필요한 정보는 이 정도..?
        temp = {
            "ODER_NO": "12345678",  # 주문번호
            "CNTG_YN": "2",  # 체결여부 (1=주문/정정/취소/거부, 2=체결)
        }

        if temp["CNTG_YN"] == "2":  # 체결된 주문만 처리
            order_no = temp["ODER_NO"]
            # 주문번호로 TradeDB에서 해당 주문 조회
            trade_record = TradeDB.get(self.db, trade_id=order_no)
            if trade_record:
                # 체결된 주문의 상태를 '체결'로 업데이트
                TradeDB.update(
                    self.db,
                    trade_record.trade_id,
                    status=TradeStatus.EXECUTED.value,
                )
                logger.info(f"Trade {trade_record.trade_id} marked as EXECUTED.")
            else:
                logger.warning(f"No trade record found for order number: {order_no}")

            # 다음 주문 넣기
            strategy = self.get_strategy(
                stock_code=trade_record.stock_code,
            )
            if strategy:
                stock_service = StockService(self.db)
                # 매수 주문이 체결된 거라면
                # 다음에 매도 + 매수 주문 넣기
                if trade_record.trade_type == TradeType.BUY.value:
                    # 다음 매도 주문 넣기
                    next_price = int(
                        strategy.buy_price * strategy.first_sell_per
                        if trade_record.split_level == 1
                        else strategy.buy_price * strategy.sell_per,
                    )
                    next_price = await self._adjust_price_to_unit(
                        trade_record.stock_code,
                        next_price,
                    )
                    quantity = strategy.invested_capital // next_price
                    try:
                        await stock_service.order(
                            stock_code=trade_record.stock_code,
                            quantity=quantity,
                            price=next_price,
                            trade_type=TradeType.SELL,
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to place sell order for {trade_record.stock_code}: {e}",
                        )

                    # 다음 매수 주문 넣기
                    if strategy.split_level + 1 < 7:  # 최대 7분할까지 허용
                        strategy.split_level += 1
                        next_price = int(
                            strategy.buy_price * strategy.buy_per,
                        )
                        next_price = await self._adjust_price_to_unit(
                            trade_record.stock_code,
                            next_price,
                        )
                        quantity = strategy.invested_capital // next_price
                        try:
                            await stock_service.order(
                                stock_code=trade_record.stock_code,
                                quantity=quantity,
                                price=next_price,
                                trade_type=TradeType.BUY,
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to place buy order for {trade_record.stock_code}: {e}",
                            )

                        # StockStrategyDB 업데이트
                        StockStrategyDB.update(
                            self.db,
                            strategy.id,
                            split_level=strategy.split_level,
                            buy_price=next_price,
                        )

                # 매도 주문이 체결된 거라면
                # 기존 매수 주문 취소하고 새 매수 주문 넣기
                else:
                    # 기존 매수 주문 취소
                    try:
                        await stock_service.cancel_order(
                            stock_code=trade_record.stock_code,
                            trade_type=TradeType.BUY,
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to cancel buy order for {trade_record.stock_code}: {e}",
                        )

                    # 새 매수 주문 넣기
                    next_price = int(
                        strategy.buy_price / strategy.buy_per,
                    )
                    next_price = await self._adjust_price_to_unit(
                        trade_record.stock_code,
                        next_price,
                    )
                    quantity = strategy.invested_capital // next_price
                    try:
                        await stock_service.order(
                            stock_code=trade_record.stock_code,
                            quantity=quantity,
                            price=next_price,
                            trade_type=TradeType.BUY,
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to place buy order for {trade_record.stock_code}: {e}",
                        )

                    # StockStrategyDB에서 split_level 업데이트
                    if strategy.split_level == 1:
                        StockStrategyDB.update(
                            self.db,
                            strategy.id,
                            buy_price=trade_record.price * strategy.buy_per,
                        )
                    else:
                        StockStrategyDB.update(
                            self.db,
                            strategy.id,
                            split_level=strategy.split_level - 1,
                            buy_price=next_price,
                        )

    # 호가단위에 맞춰 가격 조정
    async def _adjust_price_to_unit(self, stock_code: str, price: int) -> int:
        stock_service = StockService(self.db)
        aspr_unit = await stock_service.get_price_unit(stock_code)
        if (price % aspr_unit) != 0:
            return ((price // aspr_unit) + 1) * aspr_unit
        return (price // aspr_unit) * aspr_unit
