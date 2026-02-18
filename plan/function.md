## 상세 기능 명세

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
