제공해주신 `CSS_기획서.md`의 형식을 기반으로, 앞서 우리가 논의했던 **개선된 ERD 구조(설정-상태-기록 분리)**와 **현금 흐름 중심의 로직**을 반영하여 새롭게 작성한 기획서입니다.

---

# Custom Seven Split (CSS) 개발 기획서 v2.1

---

## 1. 프로젝트 개요

- **프로젝트명:** Custom Seven Split (CSS)
- **목표:** 한국투자증권 REST API를 활용하여 박성현 작가의 ‘세븐 스플릿’ 투자 기법을 자동화하고, 웹 대시보드를 통해 직관적인 손익 현황을 모니터링한다.
- **핵심 가치:** 감정을 배제한 기계적 매매, 다중 계좌(가상 분할) 관리의 편의성 제공, 정확한 실현 손익과 투자 원금 관리
- **개발 환경:** GitHub Codespaces (Linux/Cloud), VS Code

---

## 2. 기술 스택

| 구분 | 기술 / 도구 | 버전 | 선정 이유 |
| --- | --- | --- | --- |
| **Frontend** | React (Vite) | 18.x + | 빠른 HMR, 컴포넌트 기반 SPA |
| **UI Framework** | Tailwind CSS + shadcn/ui | 3.x | 직관적인 디자인 시스템, 빠른 UI 개발 |
| **Backend** | Python FastAPI | 0.110+ | 비동기 처리, 자동 Swagger 문서화, 타입 힌트 |
| **Broker API** | 한국투자증권 KIS Developers | REST v1 | Linux 호환, 웹소켓 및 REST API 지원 |
| **Database** | SQLite | 3.x | 파일 기반, 설정-상태-기록 분리 구조에 최적화 |
| **ORM** | SQLAlchemy | 2.0+ | 선언적 모델 매핑, 데이터 정합성 보장 |
| **State Mgt** | TanStack Query v5 | 5.x | 서버 상태 동기화, 자동 리패칭 |
| **Scheduler** | APScheduler | 3.10+ | 장중 주기적 감시 및 데이터 스냅샷 |
| **HTTP Client** | httpx (Backend) / Axios (Frontend) | — | 비동기 지원, 타임아웃 제어 |

---

## 3. 시스템 아키텍처

### 3.1 전체 구조도

```
┌─────────────────────────────────────────────────────────┐
│                  GitHub Codespaces                        │
│                                                           │
│  ┌──────────────┐         ┌──────────────────────────┐   │
│  │  React SPA   │  Axios  │     FastAPI Server        │   │
│  │  :5173       │◄───────►│     :8000                 │   │
│  │              │         │                            │   │
│  │  - Dashboard │         │  ┌─────────────────────┐  │   │
│  │  - Settings  │         │  │  API Router Layer    │  │   │
│  │  - History   │         │  └────────┬────────────┘  │   │
│  └──────────────┘         │           │                │   │
│                           │  ┌────────▼────────────┐  │   │
│                           │  │  Service Layer       │  │   │
│                           │  │  - TradeEngine       │  │   │
│                           │  │  - CashFlowManager   │  │   │
│                           │  └────────┬────────────┘  │   │
│                           │           │                │   │
│                           │  ┌────────▼────────────┐  │   │
│                           │  │  Repository Layer    │  │   │
│                           │  └────────┬────────────┘  │   │
│                           │           │                │   │
│                           │  ┌────────▼────────────┐  │   │
│                           │  │  sevensplit.db       │  │   │
│                           │  │  (SQLite)            │  │   │
│                           │  └─────────────────────┘  │   │
│                           │                            │   │
│                           │  ┌─────────────────────┐  │   │
│                           │  │  APScheduler         │  │   │
│                           │  └─────────┬───────────┘  │   │
│                           └─────────────┼──────────────┘   │
│                                         │ HTTPS
                                ┌─────────▼───────────┐
                                │  KIS Developers API  │
                                └──────────────────────┘
```

### 3.2 데이터 흐름 (Core Logic)

```
[Price Watcher] ──▶ [KIS API] ──▶ [현재가 수신]
       │
       ▼
[TradeEngine]
   1. StockStrategy 확인 (매수 갭, 익절 목표)
   2. VirtualBalance 확인 (현재 1~7번 계좌 보유 현황)
   3. 판단:
      ├─ 매수: 이전 차수 대비 -N% 하락 시 ──▶ [매수 주문] ──▶ [VirtualBalance 추가]
      └─ 매도: 개별 차수 목표 +N% 도달 시 ──▶ [매도 주문] ──▶ [VirtualBalance 삭제]
                                                         ──▶ [TradeHistory 기록]
```

---

## 4. 데이터베이스 스키마 (ERD v2.1)

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

---

## 5. 상세 기능 명세

### Module A: 인증 및 시스템 설정
- **API 키 관리:** 암호화하여 DB 저장 또는 환경변수 로딩.
- **자동 로그인:** 스케줄러를 통해 Access Token 만료 전 자동 갱신.
- **모의/실전 전환:** 설정 변경만으로 환경 전환 가능.

### Module B: 세븐 스플릿 엔진 (TradeEngine)
- **매수 로직 (Buying):**
    - `StockStrategy`의 `gap_ratio` 참조.
    - 직전 차수(`VirtualBalance` 중 가장 높은 `split_number`) 매수가 대비 하락 시 매수.
    - 매수 체결 시 `VirtualBalance`에 새로운 차수(`split_number + 1`) 레코드 생성.
- **매도 로직 (Selling):**
    - `VirtualBalance`의 모든 보유 차수를 순회.
    - 현재가가 `avg_price * (1 + target_return)` 이상인 차수만 선별하여 매도 주문.
    - **선입선출 회피 처리:** 증권사는 먼저 산 주식을 팔지만, DB 상에서는 해당 차수(`split_number`) 데이터를 삭제하고 수익을 확정(`TradeHistory`)함.
- **동기화 (Sync):**
    - 프로그램 시작 시 실제 KIS 잔고와 `VirtualBalance` 총합 비교.
    - 불일치 시 사용자에게 알림 및 수동 보정 UI 제공.

### Module C: 자산 및 현금 흐름 관리
- **입출금 기록 (Ledger):**
    - 사용자가 HTS/MTS로 입금 후, 웹 대시보드에서 `[자금 추가]` 버튼으로 기록.
    - `CashFlow` 테이블에 `DEPOSIT`으로 저장되어 "투자 원금" 계산에 사용.
- **배당금 관리:**
    - 배당금 수령 시 `[배당금 기록]` 기능을 통해 `CashFlow`에 `DIVIDEND`로 저장. (수익으로 간주)
- **수익 현황판:**
    - **확정 수익:** `TradeHistory`의 `realized_profit` 합계.
    - **투자 수익률(ROI):** `(현재 총자산 - 누적 순입금액) / 누적 순입금액`.

---

## 6. 디렉토리 구조

```
Custom-Seven-Split/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/          # 라우터 (auth, strategy, trade, dashboard)
│   │   ├── core/                   # 설정 (config, exceptions)
│   │   ├── db/                     # DB 연결 (session)
│   │   ├── models/                 # SQLAlchemy 모델 (schema v2.1 반영)
│   │   ├── schemas/                # Pydantic DTO
│   │   ├── services/
│   │   │   ├── kis_client.py       # KIS API 통신
│   │   │   ├── trade_engine.py     # 매매 로직 (Core)
│   │   │   ├── asset_manager.py    # CashFlow 및 잔고 관리
│   │   │   └── scheduler.py        # 주기적 작업
│   │   └── main.py
│   ├── sevensplit.db               # SQLite DB
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── dashboard/          # 자산 현황, 스플릿 보드
│   │   │   ├── strategy/           # 종목 설정 폼
│   │   │   └── history/            # 거래 내역 및 입출금 관리
│   │   ├── hooks/                  # TanStack Query (useAsset, useTrade...)
│   │   └── pages/
│   │       ├── Dashboard.jsx
│   │       ├── Strategy.jsx
│   │       └── AssetHistory.jsx
│   └── vite.config.js
└── .devcontainer/                  # Codespaces 설정
```

---

## 7. 개발 로드맵

### Phase 1: 기본 환경 및 데이터 구조 (D+1 ~ D+3)
1.  Codespace 환경 구성 (Python, React).
2.  **ERD v2.1** 기반 SQLAlchemy 모델링 및 마이그레이션.
3.  KIS API 연동 (토큰 발급, 현재가 조회).

### Phase 2: 핵심 로직 구현 (D+4 ~ D+7)
1.  `StockStrategy` CRUD API 구현.
2.  `CashFlow` 입출금 기록 API 구현.
3.  **`TradeEngine` 구현 (가장 중요):**
    - 가상 잔고(`VirtualBalance`) 기반 매수/매도 판단 로직 작성.
    - KIS 모의투자 API를 이용한 주문 테스트.

### Phase 3: 스케줄러 및 동기화 (D+8 ~ D+10)
1.  APScheduler 연동 (장중 감시, 장 마감 정산).
2.  `DailySummary` 스냅샷 생성 로직.
3.  앱 시작 시 잔고 검증(Sync Check) 로직.

### Phase 4: 프론트엔드 대시보드 (D+11 ~ D+14)
1.  종합 자산 현황 카드 (총자산, 원금, 실현수익).
2.  **세븐 스플릿 비주얼라이저:** 종목별 1~7번 계좌 상태를 시각적으로 표현 (신호등 형태).
3.  매매 기록 및 입출금 관리 UI.

### Phase 5: 안정화 및 배포 (D+15 ~ )
1.  예외 처리 강화 (API 오류, 네트워크 이슈).
2.  모의투자 환경에서 24시간 자동매매 테스트.
3.  README 작성 및 마무리.

---

## 8. 참고 사항 (Developer Note)

1.  **금융결제원 API 미사용:** 은행 이체 기능은 포함하지 않으며, HTS/MTS 이체 후 프로그램에 **'기록'**하는 방식으로 구현합니다.
2.  **선입선출 문제 해결:** 프로그램상에서는 4번 계좌를 판 것으로 처리하지만, 증권사 실제 잔고는 가장 오래된 주식이 빠져나갑니다. 이로 인한 평단가 불일치는 **`VirtualBalance` 테이블을 신뢰**하는 것으로 해결합니다.
3.  **데이터 백업:** `sevensplit.db` 파일이 곧 자산 장부이므로, 주기적으로 Git에 커밋하거나 백업하는 기능을 고려해야 합니다.