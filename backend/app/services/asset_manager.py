from sqlalchemy.orm import Session
from app.models import base
from app.services.kis_client import KISClient
from datetime import date, datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class AssetManager:
    def __init__(self, db: Session):
        """
        지금 부족한 것 : KIS 관련 함수
        """
        self.db = db
        self.settings = self._get_settings()
        self.kis_client = None
        if self.settings and self.settings.app_key and self.settings.app_secret and self.settings.account_num:
            self.kis_client = KISClient(
                app_key=self.settings.app_key,
                app_secret=self.settings.app_secret,
                account_num=self.settings.account_num,
                is_virtual=self.settings.is_virtual
            )
        else:
            logger.warning("KIS Client not initialized due to missing system settings.")

    # 시스템 설정값 불러오기
    def _get_settings(self):
        return self.db.query(base.SystemSetting).first()

    # 현시점 전체 자산 불러오기
    async def _get_current_total_asset(self) -> int:
        total_asset = 0
        
        # Get current cash balance from KIS (simplified, assuming available)
        # For a full implementation, this would involve KIS API call for current cash
        current_cash = 0 # Placeholder for actual cash from KIS

        # Sum virtual balances' current market value
        strategies = self.db.query(base.StockStrategy).all()
        for strategy in strategies:
            current_price = 0
            if self.kis_client:
                try:
                    # KIS로 현재 감시중인 종목의 현재가 조회
                    current_price = await self.kis_client.get_current_price(strategy.stock_code)
                except Exception as e:
                    logger.error(f"Failed to get current price for {strategy.stock_code}: {e}")
                    continue
            
            # 그 중에서 
            balances = self.db.query(base.VirtualAccount).filter(base.VirtualAccount.stock_code == strategy.stock_code).all()
            for balance in balances:
                total_asset += balance.quantity * current_price
        
        # Add current cash (placeholder)
        total_asset += current_cash
        
        return total_asset

    # 일별 자산 스넵샷 추가
    async def update_daily_summary(self):
        today = date.today()
        logger.info(f"Updating daily summary for {today}...")

        # 1. Calculate Net Deposit (Total Invested)
        deposits = self.db.query(base.CashFlow).filter(base.CashFlow.flow_type == "DEPOSIT").sum(base.CashFlow.amount) or 0
        withdrawals = self.db.query(base.CashFlow).filter(base.CashFlow.flow_type == "WITHDRAW").sum(base.CashFlow.amount) or 0
        net_deposit = deposits - withdrawals

        # 2. Get Current Total Asset
        current_total_asset = await self._get_current_total_asset()

        # 3. Calculate Daily Profit
        # Get yesterday's summary for daily profit calculation
        yesterday = today - timedelta(days=1)
        previous_summary = self.db.query(base.DailySummary).filter(base.DailySummary.date == yesterday).first()
        
        daily_profit = 0
        if previous_summary:
            # Daily profit = (Today's total asset - Yesterday's total asset) - (Today's net cash flow adjustment)
            # For simplicity, let's assume daily profit is current_total_asset - net_deposit if it's the first record
            # or (current_total_asset - previous_summary.total_asset) for subsequent days
            daily_profit = current_total_asset - previous_summary.total_asset
            
            # Adjust for cash flow on the current day
            today_deposits = self.db.query(base.CashFlow).filter(base.CashFlow.flow_type == "DEPOSIT", base.CashFlow.created_at >= datetime.combine(today, datetime.min.time())).sum(base.CashFlow.amount) or 0
            today_withdrawals = self.db.query(base.CashFlow).filter(base.CashFlow.flow_type == "WITHDRAW", base.CashFlow.created_at >= datetime.combine(today, datetime.min.time())).sum(base.CashFlow.amount) or 0
            daily_cash_flow_adjustment = today_deposits - today_withdrawals
            
            daily_profit -= daily_cash_flow_adjustment
        else:
            # If no previous summary, daily profit is simply total asset minus net deposit
            daily_profit = current_total_asset - net_deposit

        # 4. Create or Update DailySummary
        daily_summary = self.db.query(base.DailySummary).filter(base.DailySummary.date == today).first()
        if daily_summary:
            daily_summary.total_asset = current_total_asset
            daily_summary.total_invested = net_deposit
            daily_summary.daily_profit = daily_profit
        else:
            daily_summary = base.DailySummary(
                date=today,
                total_asset=current_total_asset,
                total_invested=net_deposit,
                daily_profit=daily_profit
            )
            self.db.add(daily_summary)
        
        self.db.commit()
        self.db.refresh(daily_summary)
        logger.info(f"Daily summary updated: {daily_summary.date}, Asset: {daily_summary.total_asset}, Invested: {daily_summary.total_invested}, Daily Profit: {daily_summary.daily_profit}")
