from sqlalchemy.orm import Session
from app.models import base
from app.db.stock_strategy_db import StockStrategyDB
from app.db.trade_check_db import TradeCheckDB
from app.services.asset_service import AssetService
from app.lib.kis_client import KISClient
from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class CSSTradeService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = self._get_settings()
        if self.settings and self.settings.app_key and self.settings.app_secret and self.settings.account_num:
            self.kis_client = KISClient(
                app_key=self.settings.app_key,
                app_secret=self.settings.app_secret,
                account_num=self.settings.account_num,
                is_virtual=self.settings.is_virtual
            )
        else:
            self.kis_client = None

    def _get_settings(self):
        return self.db.query(base.SystemSetting).first()

    def is_market_open(self):
        """
        간단한 개장시간 체크 (09:00 ~ 15:30)
        """
        now = datetime.now()
        if now.weekday() >= 5: # 주말
            return False
        current_time = now.time()
        return current_time >= datetime.strptime("09:00", "%H:%M").time() and current_time <= datetime.strptime("15:30", "%H:%M").time()

    # 종목 감시 전략 생성
    async def create_strategy(self, stock_code: str, invested_capital: int, buy_price: int, buy_per: float = 0.97, first_sell_per: float = 1.1, sell_per: float = 1.05):
        """
        stock_strategy_db에 새 Row를 추가
        if 개장시간:
            KIS로 주식 주문 요청
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
            sell_per=sell_per
        )

        if self.is_market_open() and self.kis_client:
            quantity = invested_capital // buy_price
            if quantity > 0:
                try:
                    await self.kis_client.place_order(stock_code, quantity, buy_price, side="BUY")
                    TradeCheckDB.create(self.db, stock_code, "BUY", buy_price, quantity, status=0)
                except Exception as e:
                    logger.error(f"Failed to place order for {stock_code}: {e}")

        return strategy

    # 종목 감시 전략 수정
    def change_strategy(self, stock_code: str, buy_price: Optional[int] = None, buy_per: Optional[float] = None, first_sell_per: Optional[float] = None, sell_per: Optional[float] = None):
        """
        stock_strategy_db에서 stock_code로 Row 찾고 부분 변경
        """
        strategy = StockStrategyDB.get_by_stock_code(self.db, stock_code)
        if not strategy:
            return None

        update_kwargs = {}
        if buy_price is not None:
            update_kwargs['buy_price'] = buy_price
        if buy_per is not None:
            update_kwargs['buy_per'] = buy_per
        if first_sell_per is not None:
            update_kwargs['first_sell_per'] = first_sell_per
        if sell_per is not None:
            update_kwargs['sell_per'] = sell_per
        
        if update_kwargs:
            StockStrategyDB.update(self.db, strategy.id, **update_kwargs)
            return StockStrategyDB.get(self.db, strategy.id)
        return strategy

    # 종목 감시 전략 삭제
    def delete_strategy(self, stock_code: str):
        """
        stock_strategy_db에서 stock_code로 Row 찾기, 해당 Row 삭제
        """
        strategy = StockStrategyDB.get_by_stock_code(self.db, stock_code)
        if strategy:
            return StockStrategyDB.delete(self.db, strategy.id)
        return False

    # 종목 감시 전략 조회
    def get_stratagy(self, stock_code: str):
        """
        stock_strategy_db에서 stock_code로 Row 찾기, Row 반환
        """
        return StockStrategyDB.get_by_stock_code(self.db, stock_code)

    # 주문 체결 결과 확인 테이블 조회
    def get_trade_check_list(self, stock_code: Optional[str] = None, status: Optional[int] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """
        특정 조건에 따라 Row 조회
        """
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
    async def check_trade_result(self, stock_code: str, trade_type: str, execution_price: int, execution_qty: int):
        """
        웹소켓에 등록된 감시 종목이 매수가/매도가에 도달하면 실행됨
        """
        strategy = StockStrategyDB.get_by_stock_code(self.db, stock_code)
        if not strategy:
            return

        # 매수/매도 대기 중인 항목을 찾음 (status=0)
        pending_trades = [t for t in self.get_trade_check_list(stock_code=stock_code, status=0) if t.type == trade_type]
        if not pending_trades:
            return
            
        target_trade = pending_trades[0]
        TradeCheckDB.update(self.db, target_trade.id, status=1)

        asset_service = AssetService(self.db)
        max_split_level = 7  # 하드코딩된 값 (수정 가능)

        if trade_type == "BUY":
            sell_price = int(strategy.buy_price * strategy.first_sell_per) if strategy.split_level == 1 else int(strategy.buy_price * strategy.sell_per)
            
            # 매도 예약 (실제로는 예약 주문 혹은 개장 시 즉시 매도)
            if self.is_market_open() and self.kis_client:
                try:
                    await self.kis_client.place_order(stock_code, execution_qty, sell_price, side="SELL")
                    TradeCheckDB.create(self.db, stock_code, "SELL", sell_price, execution_qty, status=0)
                except Exception as e:
                    logger.error(f"Failed to place sell order: {e}")

            asset_service.record_buy_stock(strategy.split_level, stock_code, execution_price, execution_qty)

            if strategy.split_level + 1 < max_split_level:
                new_split_level = strategy.split_level + 1
                new_buy_price = int(strategy.buy_price * strategy.buy_per)
                StockStrategyDB.update(self.db, strategy.id, split_level=new_split_level, buy_price=new_buy_price)

                # 새로운 매수 주문 등록
                new_qty = strategy.invested_capital // new_buy_price
                if new_qty > 0 and self.is_market_open() and self.kis_client:
                    try:
                        await self.kis_client.place_order(stock_code, new_qty, new_buy_price, side="BUY")
                        TradeCheckDB.create(self.db, stock_code, "BUY", new_buy_price, new_qty, status=0)
                    except Exception as e:
                        logger.error(f"Failed to place next buy order: {e}")

        elif trade_type == "SELL":
            # 매수 주문 취소 로직
            cancel_targets = [t for t in pending_trades if t.type == "BUY" and t.id != target_trade.id]
            for ct in cancel_targets:
                TradeCheckDB.update(self.db, ct.id, status=2)
                # 실제 KIS 주문 취소 로직 추가 필요할 수 있음
                
            asset_service.record_sell_stock(strategy.split_level, stock_code, execution_price, execution_qty, target_trade.id)

            if strategy.split_level > 1:
                new_split_level = strategy.split_level - 1
                new_buy_price = int(strategy.buy_price / strategy.buy_per)
                StockStrategyDB.update(self.db, strategy.id, split_level=new_split_level, buy_price=new_buy_price)

                # 매도 후 다시 이전 split level에 대한 매수 주문
                new_qty = strategy.invested_capital // new_buy_price
                if new_qty > 0 and self.is_market_open() and self.kis_client:
                    try:
                        await self.kis_client.place_order(stock_code, new_qty, new_buy_price, side="BUY")
                        TradeCheckDB.create(self.db, stock_code, "BUY", new_buy_price, new_qty, status=0)
                    except Exception as e:
                        logger.error(f"Failed to place buy order after sell: {e}")
