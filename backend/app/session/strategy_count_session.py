from sqlalchemy.orm import Session
from app.table.strategy_count_view import StrategyCountView
from typing import Optional, List

class StrategyCountSession:
    def __init__(self, db: Session):
        self.db = db

    def get_by_account(self, account_number: str) -> Optional[StrategyCountView]:
        """특정 계좌의 전략 개수 조회"""
        return self.db.query(StrategyCountView).filter(
            StrategyCountView.account_number == account_number
        ).first()

    def get_all(self) -> List[StrategyCountView]:
        """모든 계좌의 전략 개수 목록 조회"""
        return self.db.query(StrategyCountView).all()
