from sqlalchemy.orm import Session
from app.table.balance_table import Balance
from app.table.balance_summary_view import BalanceSummary

def get_balance_with_summary(db: Session, account_number: str):
    """
    Balance 테이블과 BalanceSummary 뷰를 account_number와 split_level로 조인하여 조회합니다.
    """
    return db.query(Balance, BalanceSummary.investment)\
        .join(BalanceSummary, 
              (Balance.account_number == BalanceSummary.account_number) & 
              (Balance.split_level == BalanceSummary.split_level))\
        .filter(Balance.account_number == account_number)\
        .all()
