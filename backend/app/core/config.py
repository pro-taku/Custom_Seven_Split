import os
from enum import Enum
from typing import Optional

from fastapi.logger import logger
from ruamel.yaml import YAML

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

YAML_FILE_PATH = os.path.join(BASE_DIR, "kis_property.yaml")

yaml = YAML()
yaml.preserve_quotes = True

MAX_SPLIT_LEVEL = 7  # 최대 분할 레벨 (수정 가능)

# Global environment variable for KIS API (V: Virtual, R: Real)
GLOBAL_ENV = os.getenv("KIS_ENV", "V")
IS_HOLIDAY = False # 휴장일 여부

############################################################################


class TradeType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(Enum):
    PENDING = 0  # 대기중
    EXECUTED = 1  # 체결
    CANCELED = 2  # 취소


class CashFlowType(Enum):
    INPUT = "input"
    OUTPUT = "output"
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    INTEREST = "interest"


############################################################################

# 이 시스템은 SQLite를 DB로 쓰고 있다.
# 이건 backend 폴더에서 db 파일의 위치를 뜻한다
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sevensplit.db")

############################################################################

# KIS 실전/모의투자 도메인
KIS_REAL_DOMAIN = "https://openapi.koreainvestment.com:9443"
KIS_REAL_WS_DOMAIN = "ws://ops.koreainvestment.com:21000"
KIS_VIRTUAL_DOMAIN = "https://openapivts.koreainvestment.com:29443"
KIS_VIRTUAL_WS_DOMAIN = "ws://ops.koreainvestment.com:31000"

CUSTOMER_TYPE = "P"  # 고객 타입 - 개인


# 주문 구분
class CodeEnum(Enum):
    LIMIT_ORDER = "00"  # 지정가 주문
    MARKET_ORDER = "01"  # 시장가 주문
    ORDER_CORRECT = "03"  # 주문 정정
    ORDER_CANCEL = "02"  # 주문 취소


class TR(Enum):
    """
    TR ID 모음
    - KS : Korea Stock (국내주식)
    - R : Real (실전투자)
    - V : Virtual (모의투자)
    """

    TR_KS_SELL_R = "TTTC0011U"  # 실전 매도
    TR_KS_SELL_V = "VTTC0011U"  # 모의 매도
    TR_KS_BUY_R = "TTTC0012U"  # 실전 매수
    TR_KS_BUY_V = "VTTC0012U"  # 모의 매수
    TR_KS_BUY_POSSIBLE_R = "TTTC8908R"  # 실전 매수 가능 여부
    TR_KS_BUY_POSSIBLE_V = "VTTC8908R"  # 모의 매수 가능 여부
    TR_KS_FIX_CANCEL_R = "TTTC0013U"  # 실전 정정/취소
    TR_KS_FIX_CANCEL_V = "VTTC0013U"  # 모의 정정/취소
    TR_KS_RESV_ORDER_R = "CTSC0008U"  # 실전 예약 매매 (모의 지원 X)
    TR_KS_RESV_CANCEL_R = "CTSC0009U"  # 실전 예약 취소 (모의 지원 X)
    TR_KS_RESV_FIX_R = "CTSC0013U"  # 실전 예약 정정 (모의 지원 X)
    TR_KS_RESV_SELECT_R = "CTSC0004R"  # 실전 예약 조회 (모의 지원 X)
    TR_KS_ACCOUNT_R = "TTTC8434R"  # 실전 주식잔고조회
    TR_KS_ACCOUNT_V = "VTTC8434R"  # 모의 주식잔고조회
    TR_KS_ORDER_CHECK_R = "H0STCNI0"  # 실전 실시간 체결통보
    TR_KS_ORDER_CHECK_V = "H0STCNI9"  # 모의 실시간 체결통보
    TR_KS_PRICE_R = "FHKST01010100"  # 실전 주식 현재가
    TR_KS_PRICE_V = "FHKST01010100"  # 모의 주식 현재가
    TR_KS_RT_PRICE_R = "H0STASP0"  # 실전 실시간 주식 호가
    TR_KS_RT_PRICE_V = "H0STASP0"  # 모의 실시간 주식 호가
    TR_KS_HOLIDAY = "CTRP6011R"  # 국내 휴장일 조회


############################################################################


def save_data(key: str, value: str):
    try:
        if not os.path.exists(YAML_FILE_PATH):
            logger.error(f"YAML file not found: {YAML_FILE_PATH}")
            return

        with open(YAML_FILE_PATH, encoding="utf-8") as f:
            data = yaml.load(f)

        if data is None:
            data = {}

        data[key] = value

        with open(YAML_FILE_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        logger.debug(f"Saved {key} to {YAML_FILE_PATH}")
    except Exception as e:
        logger.error(f"Error saving data to YAML: {e}")


def read_data(key: str) -> Optional[str]:
    try:
        if not os.path.exists(YAML_FILE_PATH):
            logger.error(f"YAML file not found: {YAML_FILE_PATH}")
            return None

        with open(YAML_FILE_PATH, encoding="utf-8") as f:
            data = yaml.load(f)

        if data and key in data:
            return str(data[key])
    except Exception as e:
        logger.error(f"Error reading data from YAML: {e}")

    return None
