import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import MAX_SPLIT_LEVEL
from app.db.account_db import AccountDB
from app.db.stock_strategy_db import StockStrategyDB
from app.db.trade_check_db import TradeCheckDB
from app.lib.kis.client import KISClient
from app.services.asset_service import AssetService

logger = logging.getLogger(__name__)

# Global environment variable, set from main.py
from app.core.config import GLOBAL_ENV


class CSSTradeService:
    def __init__(self, db: Session):
        self.db = db
        self.kis_client = KISClient(env=GLOBAL_ENV)  # KISClient 인스턴스 초기화

    # 4주마다 예약주문 갱신
    async def refresh_strategies(self):
        """모든 전략의 예약주문을 4주(28일) 단위로 갱신 (실전투자 전용)"""
        if not self.kis_client or self.kis_client.env == "V":
            logger.warning("Reservation orders are only supported in Real environment.")
            return

        strategies = self.get_strategy_all()
        # 4주 뒤 날짜 계산 (YYYYMMDD)
        from datetime import timedelta

        target_date = (datetime.now() + timedelta(days=28)).strftime("%Y%m%d")

        for strategy in strategies:
            # 1. 매수 예약 주문 (현재 분할 레벨에 따른 매수 가격)
            # Seven Split 전략에 따라 현재 split_level에 해당하는 매수 주문을 넣음
            # (이미 1단계는 샀을 것이므로, 다음 단계 매수 주문)
            if strategy.split_level < MAX_SPLIT_LEVEL:
                buy_price = int(strategy.buy_price * strategy.buy_per)
                quantity = strategy.invested_capital // buy_price
                if quantity > 0:
                    try:
                        await self.kis_client.order_resv(
                            pdno=strategy.stock_code,
                            sll_buy_dvsn_cd="02",  # 매수
                            ord_qty=quantity,
                            ord_unpr=buy_price,
                            resv_qty_all_ord_yn="Y",
                            resv_ord_dvsn_cd="01",  # 지정가
                            resv_ord_tp_cd="03",  # 기간예약(지정일)
                            resv_ord_trgt_dt=target_date,
                        )
                        logger.info(
                            f"Refreshed BUY resv order for {strategy.stock_code} at {buy_price}",
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to refresh BUY resv order for {strategy.stock_code}: {e}",
                        )

            # 2. 매도 예약 주문 (보유 중인 수량에 대해)
            # 현재 split_level에 해당하는 보유 종목 조회
            accounts = AccountDB.select_virtual_account(self.db, strategy.split_level)
            for acc in accounts:
                if acc.stock_code == strategy.stock_code:
                    sell_price = (
                        int(strategy.buy_price * strategy.first_sell_per)
                        if strategy.split_level == 1
                        else int(strategy.buy_price * strategy.sell_per)
                    )
                    try:
                        await self.kis_client.order_resv(
                            pdno=strategy.stock_code,
                            sll_buy_dvsn_cd="01",  # 매도
                            ord_qty=acc.count,
                            ord_unpr=sell_price,
                            resv_qty_all_ord_yn="Y",
                            resv_ord_dvsn_cd="01",  # 지정가
                            resv_ord_tp_cd="03",  # 기간예약(지정일)
                            resv_ord_trgt_dt=target_date,
                        )
                        logger.info(
                            f"Refreshed SELL resv order for {strategy.stock_code} at {sell_price}",
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to refresh SELL resv order for {strategy.stock_code}: {e}",
                        )

    # 수정 요망
    def is_market_open(self):
        """간단한 개장시간 체크 (09:00 ~ 15:30)"""
        now = datetime.now()
        if now.weekday() >= 5:  # 주말
            return False
        current_time = now.time()
        return (
            current_time >= datetime.strptime("09:00", "%H:%M").time()
            and current_time <= datetime.strptime("15:30", "%H:%M").time()
        )

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
        """
        stock_strategy_db에 새 Row를 추가

        if 개장시간:

        - KIS로 주식 주문 요청

          trade_check_db에 새 Row를 추가 (status=0)
        """
        strategy = StockStrategyDB.create(
            self.db,
            stock_code=stock_code,
            split_level=1,
            invested_capital=invested_capital,
            buy_price=buy_price,
            buy_per=buy_per,
            first_sell_per=first_sell_per,
            sell_per=sell_per,
        )

        if self.is_market_open() and self.kis_client:
            quantity = invested_capital // buy_price
            if quantity > 0:
                try:
                    await self.kis_client.order_cash(
                        stock_code,
                        quantity,
                        buy_price,
                        side="BUY",
                    )
                    TradeCheckDB.create(
                        self.db,
                        stock_code,
                        "BUY",
                        buy_price,
                        quantity,
                        status=0,
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
        """stock_strategy_db에서 stock_code로 Row 찾고 부분 변경"""
        strategy = StockStrategyDB.get_by_stock_code(self.db, stock_code)
        if not strategy:
            return None

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

    # 종목 감시 전략 전체 조회
    def get_strategy_all(self):
        """stock_strategy_db의 모든 Row 반환"""
        return StockStrategyDB.get_all(self.db)

    # 종목 감시 전략 조회
    def get_strategy(self, stock_code: str):
        """stock_strategy_db에서 stock_code로 Row 찾기, Row 반환"""
        return StockStrategyDB.get_by_stock_code(self.db, stock_code)

    # 주문 체결 결과 확인 테이블 조회
    def get_trade_check_list(
        self,
        stock_code: str | None = None,
        status: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ):
        """특정 조건에 따라 Row 조회"""
        query = self.db.query(TradeCheckDB)
        if stock_code:
            query = query.filter(TradeCheckDB.stock_code == stock_code)
        if status is not None:
            query = query.filter(TradeCheckDB.status == status)
        if start_date:
            query = query.filter(TradeCheckDB.created_at >= start_date)
        if end_date:
            query = query.filter(TradeCheckDB.created_at <= end_date)

        return query.all()

    # [실시간] 주문 체결 확인
    async def check_trade_result(
        self,
        stock_code: str,
        trade_type: str,
        execution_price: int,
        execution_qty: int,
    ):
        """웹소켓에 등록된 감시 종목이 매수가/매도가에 도달하면 실행됨"""
        strategy = StockStrategyDB.get_by_stock_code(self.db, stock_code)
        if not strategy:
            return

        # 매수/매도 대기 중인 항목을 찾음 (status=0)
        pending_trades = [
            t
            for t in self.get_trade_check_list(stock_code=stock_code, status=0)
            if t.type == trade_type
        ]
        if not pending_trades:
            return

        target_trade = pending_trades[0]
        TradeCheckDB.update(self.db, target_trade.trade_id, status=1)

        asset_service = AssetService(self.db)

        if trade_type == "BUY":
            # 호가단위를 맞춰야 함
            sell_price = (
                int(strategy.buy_price * strategy.first_sell_per)
                if strategy.split_level == 1
                else int(strategy.buy_price * strategy.sell_per)
            )

            # 매도 예약 (실제로는 예약 주문 혹은 개장 시 즉시 매도)
            if self.is_market_open() and self.kis_client:
                try:
                    await self.kis_client.order_cash(
                        stock_code,
                        execution_qty,
                        sell_price,
                        side="SELL",
                    )
                    TradeCheckDB.create(
                        self.db,
                        stock_code,
                        "SELL",
                        sell_price,
                        execution_qty,
                        status=0,
                    )
                except Exception as e:
                    logger.error(f"Failed to place sell order: {e}")

            asset_service.record_buy_stock(
                strategy.split_level,
                stock_code,
                execution_price,
                execution_qty,
            )

            if strategy.split_level + 1 < MAX_SPLIT_LEVEL:
                new_split_level = strategy.split_level + 1
                # 호가단위 맞춰야 함
                new_buy_price = int(strategy.buy_price * strategy.buy_per)
                StockStrategyDB.update(
                    self.db,
                    strategy.id,
                    split_level=new_split_level,
                    buy_price=new_buy_price,
                )

                # 새로운 매수 주문 등록
                new_qty = strategy.invested_capital // new_buy_price
                if new_qty > 0 and self.is_market_open() and self.kis_client:
                    try:
                        await self.kis_client.order_cash(
                            stock_code,
                            new_qty,
                            new_buy_price,
                            side="BUY",
                        )
                        TradeCheckDB.create(
                            self.db,
                            stock_code,
                            "BUY",
                            new_buy_price,
                            new_qty,
                            status=0,
                        )
                    except Exception as e:
                        logger.error(f"Failed to place next buy order: {e}")

        elif trade_type == "SELL":
            # 매수 주문 취소 로직
            cancel_targets = [
                t
                for t in pending_trades
                if t.type == "BUY" and t.trade_id != target_trade.trade_id
            ]
            for ct in cancel_targets:
                TradeCheckDB.update(self.db, ct.trade_id, status=2)
                # 실제 KIS 주문 취소 로직 추가 필요할 수 있음

            asset_service.record_sell_stock(
                strategy.split_level,
                stock_code,
                execution_price,
                execution_qty,
                target_trade.trade_id,
            )

            if strategy.split_level > 1:
                new_split_level = strategy.split_level - 1
                # 호가 단위 맞춰야 함
                new_buy_price = int(strategy.buy_price / strategy.buy_per)
                StockStrategyDB.update(
                    self.db,
                    strategy.id,
                    split_level=new_split_level,
                    buy_price=new_buy_price,
                )

                # 매도 후 다시 이전 split level에 대한 매수 주문
                new_qty = strategy.invested_capital // new_buy_price
                if new_qty > 0 and self.is_market_open() and self.kis_client:
                    try:
                        await self.kis_client.order_cash(
                            stock_code,
                            new_qty,
                            new_buy_price,
                            side="BUY",
                        )
                        TradeCheckDB.create(
                            self.db,
                            stock_code,
                            "BUY",
                            new_buy_price,
                            new_qty,
                            status=0,
                        )
                    except Exception as e:
                        logger.error(f"Failed to place buy order after sell: {e}")
