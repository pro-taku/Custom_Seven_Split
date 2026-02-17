from sqlalchemy.orm import Session
from app.models import base
from app.services.kis_client import KISClient
import logging

logger = logging.getLogger(__name__)

class TradeEngine:
    def __init__(self, db: Session):
        self.db = db
        self.settings = self._get_settings()
        if self.settings:
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

    async def run_logic(self):
        """
        Main loop for trade logic.
        """
        if not self.kis_client:
            logger.error("System settings not found. Cannot run TradeEngine.")
            return

        strategies = self.db.query(base.StockStrategy).filter(base.StockStrategy.status == "RUNNING").all()
        
        for strategy in strategies:
            try:
                await self.process_strategy(strategy)
            except Exception as e:
                logger.error(f"Error processing strategy for {strategy.stock_code}: {e}")

    async def process_strategy(self, strategy: base.StockStrategy):
        current_price = await self.kis_client.get_current_price(strategy.stock_code)
        logger.info(f"Processing {strategy.stock_name} ({strategy.stock_code}) - Current Price: {current_price}")

        # 1. Check for Sell opportunities (Target Return reached)
        balances = self.db.query(base.VirtualBalance).filter(
            base.VirtualBalance.stock_code == strategy.stock_code
        ).all()

        for balance in balances:
            target_price = balance.avg_price * (1 + strategy.target_return)
            if current_price >= target_price:
                await self.execute_sell(strategy, balance, current_price)

        # 2. Check for Buy opportunities (Gap Ratio reached)
        # Find the highest split number currently held
        max_split_held = 0
        last_buy_price = 0
        
        if balances:
            highest_split_balance = max(balances, key=lambda x: x.split_number)
            max_split_held = highest_split_balance.split_number
            last_buy_price = highest_split_balance.avg_price
        
        # If we can still split
        if max_split_held < strategy.max_split:
            should_buy = False
            if max_split_held == 0:
                # First buy - maybe just buy immediately if no balance? 
                # Or wait for a specific signal? Seven Split usually starts with first buy.
                should_buy = True
                next_split = 1
            else:
                # Buy next split if price dropped enough from last buy price
                buy_threshold = last_buy_price * (1 - strategy.gap_ratio)
                if current_price <= buy_threshold:
                    should_buy = True
                    next_split = max_split_held + 1
            
            if should_buy:
                await self.execute_buy(strategy, next_split, current_price)

    async def execute_buy(self, strategy: base.StockStrategy, split_number: int, price: int):
        quantity = strategy.invest_per_split // price
        if quantity == 0:
            logger.warning(f"Quantity is 0 for {strategy.stock_code}. Invest amount might be too small.")
            return

        logger.info(f"Executing BUY for {strategy.stock_code} split {split_number} at {price}")
        
        # In real/virtual trading:
        # order_result = await self.kis_client.place_order(strategy.stock_code, quantity, price, "BUY")
        # For now, let's assume it's successful and update DB
        
        new_balance = base.VirtualBalance(
            stock_code=strategy.stock_code,
            split_number=split_number,
            quantity=quantity,
            avg_price=price
        )
        self.db.add(new_balance)
        
        history = base.TradeHistory(
            stock_code=strategy.stock_code,
            trade_type="BUY",
            split_number=split_number,
            price=price,
            quantity=quantity
        )
        self.db.add(history)
        
        self.db.commit()

    async def execute_sell(self, strategy: base.StockStrategy, balance: base.VirtualBalance, price: int):
        logger.info(f"Executing SELL for {strategy.stock_code} split {balance.split_number} at {price}")
        
        # In real/virtual trading:
        # order_result = await self.kis_client.place_order(strategy.stock_code, balance.quantity, price, "SELL")
        
        realized_profit = (price - balance.avg_price) * balance.quantity
        
        history = base.TradeHistory(
            stock_code=strategy.stock_code,
            trade_type="SELL",
            split_number=balance.split_number,
            price=price,
            quantity=balance.quantity,
            realized_profit=realized_profit
        )
        self.db.add(history)
        
        # Delete from virtual balance
        self.db.delete(balance)
        
        self.db.commit()
