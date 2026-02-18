"""
1. 왜 Base 클래스를 따로 만드나요? (데이터 정합성 및 재사용)

데이터베이스에 저장된 데이터와 사용자가 처음 생성할 때 보내는 데이터는 구성이 조금 다릅니다.

* `CashFlowBase` (입력용): 사용자가 데이터를 입력할 때 필요한 필드들만 정의합니다.
    * 사용자가 id나 created_at을 직접 정해서 보낼 필요가 없으므로 (DB에서 자동 생성됨), 이 필드들은 제외합니다.
* `CashFlow` (출력용): Base를 상속받고, DB에서 생성된 id나 created_at 필드를 추가합니다.
    * API가 결과를 반환할 때는 "이 데이터의 ID는 무엇이고 언제 생성되었는지"를 포함해서 보여줘야 하기 때문입니다.

이렇게 분리하면 생성 API(`POST`)에서는 Base 클래스를 사용하여 불필요한 필드 입력을 막고, 조회 API(`GET`)에서는 상속받은 클래스를 사용하여 전체 정보를 보여줄 수 있어 코드가 깔끔해집니다.

----------------------------------------

2. 왜 class Config 안에 from_attributes = True를 넣나요? (ORM 호환성)

이 설정은 Pydantic이 데이터베이스 객체(SQLAlchemy 모델)를 읽을 수 있게 해주는 핵심 설정입니다.

* 기본 동작: Pydantic은 기본적으로 데이터가 Python의 딕셔너리(`dict`) 형태일 때만 데이터를 읽어올 수 있습니다 (예: data["amount"]).
* 문제점: 하지만 DB에서 가져온 데이터(SQLAlchemy 객체)는 딕셔너리가 아니라 객체(`Object`) 형태입니다. 데이터를 가져올 때 data.amount 처럼 속성(Attribute)에 접근해야 합니다.
* 해결책: from_attributes = True를 설정하면, Pydantic이 "아, 이 데이터가 딕셔너리가 아니면 객체의 속성에서 값을 읽어와야겠구나"라고 판단합니다.

결과적으로 FastAPI의 read_cash_flows 같은 함수에서 DB 객체를 별도의 변환 과정 없이 즉시 Pydantic 모델로 변환하여 클라이언트에게 전송할 수 있게 해줍니다.

"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

########################################################

# 시스템 셋팅
class SystemSettingBase(BaseModel):
    account_num: str                        # 계좌번호
    kis_key: str                            # 한투 Key
    kis_secret: str                         # 한투 secret
    is_virtual: bool = True                 # 모의투자 여부
    default_gap_ratio: float = 0.03         # 기본 매수 하락폭 (%)
    default_target_return: float = 0.05     # 기본 매도 상승폭 (%)

class SystemSetting(SystemSettingBase):
    class Config:
        from_attributes = True

########################################################

# 종목별 감시 전략
class StockStrategyBase(BaseModel):
    stock_code: str         # 종목 코드
    stock_name: str         # 종목 이름
    gap_ratio: float        # 매수 하락폭 (%)
    target_return: float    # 매도 상승폭 (%)
    invest_per_split: int   # 분할계좌당 투자금
    max_split: int = 7      # 최대 분할 매수 횟수

class StockStrategy(StockStrategyBase):
    id: int         # UID
    status: int     # 0=중단, 1=감시중

    class Config:
        from_attributes = True

########################################################

# 가상 계좌 잔고
class VirtualAccountBase(BaseModel):
    stock_code: str     # 종목 코드
    split_number: int   # 1~7 = 가상계좌차수, 0 = 일반 매매
    quantity: int       # 보유 수량
    avg_price: int      # 구매 단가

class VirtualAccount(VirtualAccountBase):
    id: int                 # UID
    created_at: datetime    # Row 생성 시기

    class Config:
        from_attributes = True

########################################################

# 거래 내역
class TradeHistoryBase(BaseModel):
    stock_code: str                         # 종목 코드
    trade_type: str                         # 거래 타입 (BUY, SELL)
    split_number: int                       # 1~7 = 가상계좌차수, 0 = 일반 매매
    price: int                              # 가격
    quantity: int                           # 수량
    realized_profit: Optional[int] = None   # 차익실현 (매수 땐 NULL, 매도 때만 기록)

class TradeHistory(TradeHistoryBase):
    id: int                 # UID
    trade_time: datetime    # Row 생성 시기

    class Config:
        from_attributes = True

########################################################

# 현금 흐름
class CashFlowBase(BaseModel):
    flow_type: str      # DEPOSIT(입금/증액), WITHDRAW(출금), DIVIDEND(배당)
    amount: int         # 금액
    memo: Optional[str] = None  # 메모

class CashFlow(CashFlowBase):
    id: int                 # UID
    created_at: datetime    # Row 생성 시기

    class Config:
        from_attributes = True

########################################################

# 일별 리포트 - 자산 내역 기록
class DailySummary(BaseModel):
    date: datetime      # 날짜
    total_asset: int    # 자산 (평가금 + 예수금)
    total_invested: int # 원금
    daily_profit: int   # 당일 손익실현

    class Config:
        from_attributes = True

########################################################

# 누적 순입금액 (투자 원금 계산용)
class CumulativeCashFlow(BaseModel):
    cumulative_deposit: int     # 누적 입금액
    cumulative_withdraw: int    # 누적 출금액
    net_deposit: int            # 순 입금액 (투자 원금)

    class Config:
        from_attributes = True

########################################################

# 총 확정 수익
class TotalRealizedProfit(BaseModel):
    total_realized_profit: int  # 총 실현 손익

    class Config:
        from_attributes = True

########################################################

# 투자 수익률 (ROI)
class ROIReport(BaseModel):
    current_total_asset: int    # 현재 총 자산 (DailySummary 또는 KIS에서 가져옴)
    net_deposit: int            # 순 입금액 (투자 원금)
    roi: float                  # 투자 수익률 (%)

    class Config:
        from_attributes = True
