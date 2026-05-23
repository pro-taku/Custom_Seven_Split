from sqlalchemy import Column, String, Integer, event, DDL
from app.core.connect import Base

class StrategyCountView(Base):
    __tablename__ = "strategy_count_view"

    account_number = Column(String(20), primary_key=True)
    strategy_count = Column(Integer)

# View 생성 SQL
# strategies 테이블에서 account_number별로 그룹화하여 개수를 셉니다.
view_ddl = DDL(
    """
    CREATE VIEW IF NOT EXISTS strategy_count_view AS
    SELECT account_number, COUNT(*) as strategy_count
    FROM strategies
    GROUP BY account_number
    """
)

# Base.metadata.create_all() 호출 시 테이블 생성 후에 뷰를 생성하도록 이벤트를 등록합니다.
event.listen(
    StrategyCountView.__table__,
    "after_create",
    view_ddl.execute_if(dialect="sqlite")
)
