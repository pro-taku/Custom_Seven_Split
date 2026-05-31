from sqlalchemy import Column, String, Integer, event, DDL
from app.core.connect import Base

class BalanceSummary(Base):
    __tablename__ = "balance_summary_view"

    account_number = Column(String(20), primary_key=True)   # 계좌 번호
    split_level = Column(Integer, primary_key=True)         # 분할 레벨
    investment = Column(Integer)    # 투자 금액 (price * quantity의 합계)

# View 생성 SQL
view_ddl = DDL(
    """
    CREATE VIEW IF NOT EXISTS balance_summary_view AS
    SELECT account_number, split_level, SUM(price * quantity) as investment
    FROM balances
    GROUP BY account_number, split_level
    """
)

# View 생성 이벤트 등록
event.listen(
    BalanceSummary.__table__,
    'after_create',
    view_ddl.execute_if(dialect='postgresql')  # PostgreSQL에서만 실행
)