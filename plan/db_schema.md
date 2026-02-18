## 데이터베이스 스키마 (ERD v3)

기존 기획서 대비 **설정(Config) / 상태(State) / 기록(History)**을 명확히 분리하여 자산 흐름 추적을 강화함.

### Group 1: 설정 및 기초 데이터

#### `system_setting` — 시스템 전역 설정
| 컬럼명 | 타입 | 설명 |
| --- | --- | --- |
| `account_num` | PK, TEXT | 실계좌번호 (8자리) |
| `app_key` | TEXT | KIS App Key |
| `app_secret` | TEXT | KIS App Secret |
| `is_virtual` | BOOLEAN | 모의투자 여부 |
| `default_gap_ratio` | REAL | 기본 매수 하락폭 (예: 0.03) |
| `default_target_return` | REAL | 기본 익절 목표 (예: 0.05) |

#### `stock_strategy` — 종목별 감시 전략
| 컬럼명 | 타입 | 설명 |
| --- | --- | --- |
| `id` | PK, INT | 고유 ID |
| `stock_code` | TEXT | 종목코드 (UNIQUE) |
| `stock_name` | TEXT | 종목명 |
| `status` | TEXT | `RUNNING`(감시중), `PAUSED`(중지) |
| `gap_ratio` | REAL | 매수 간격 (0.03 = -3%) |
| `target_return` | REAL | 목표 수익률 (0.05 = +5%) |
| `invest_per_split` | INT | 1분할당 투자금액 |
| `max_split` | INT | 최대 분할 차수 (기본 7) |

### Group 2: 현재 상태 (State)

#### `virtual_balance` — 가상 계좌 잔고 (핵심)
증권사 잔고와 별개로 프로그램이 인식하는 **논리적 계좌 상태**입니다.
| 컬럼명 | 타입 | 설명 |
| --- | --- | --- |
| `id` | PK, INT | 고유 ID |
| `stock_code` | FK, TEXT | 종목코드 |
| `split_number` | INT | 1~7 (세븐 스플릿 차수), 0 (일반) |
| `quantity` | INT | 보유 수량 |
| `avg_price` | INT | **해당 차수의 평단가** |
| `created_at` | DATETIME | 최초 매수일 |

### Group 3: 기록 및 로그 (History)

#### `trade_history` — 매매 기록 및 손익
| 컬럼명 | 타입 | 설명 |
| --- | --- | --- |
| `id` | PK, INT | 고유 ID |
| `trade_time` | DATETIME | 체결 시간 |
| `stock_code` | FK, TEXT | 종목코드 |
| `trade_type` | TEXT | `BUY`, `SELL` |
| `split_number` | INT | 거래 주체 (몇 번 계좌) |
| `price` | INT | 체결 단가 |
| `quantity` | INT | 체결 수량 |
| `realized_profit` | INT | **실현 손익** (매도 시에만 기록, 매수는 NULL) |

#### `cash_flow` — 자금 입출금 장부
실제 뱅킹이 아닌, 투자 원금 관리를 위한 **디지털 장부**입니다.
| 컬럼명 | 타입 | 설명 |
| --- | --- | --- |
| `id` | PK, INT | 고유 ID |
| `created_at` | DATETIME | 기록 시간 |
| `flow_type` | TEXT | `DEPOSIT`(입금/증액), `WITHDRAW`(출금), `DIVIDEND`(배당) |
| `amount` | INT | 금액 |
| `memo` | TEXT | 메모 (예: "월급 투자금", "삼성전자 배당") |

#### `daily_summary` — 일별 리포트
| 컬럼명 | 타입 | 설명 |
| --- | --- | --- |
| `date` | PK, DATE | 날짜 |
| `total_asset` | INT | 총 자산 (평가금 + 예수금) |
| `total_invested` | INT | 누적 원금 (`CashFlow` 집계) |
| `daily_profit` | INT | 당일 실현 손익 (`TradeHistory` 집계) |
