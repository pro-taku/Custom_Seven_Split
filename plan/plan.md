## Custom Seven Split (CSS) 개발 기획서 v3

---

### 프로젝트 개요

- **프로젝트명:** Custom Seven Split (CSS)
- **목표:** 한국투자증권 REST API를 활용하여 박성현 작가의 ‘세븐 스플릿’ 투자 기법을 자동화하고, 웹 대시보드를 통해 직관적인 손익 현황을 모니터링한다.
- **핵심 가치:** 감정을 배제한 기계적 매매, 다중 계좌(가상 분할) 관리의 편의성 제공, 정확한 실현 손익과 투자 원금 관리
- **개발 환경:** GitHub Codespaces (Linux/Cloud), VS Code

---

### 기술 스택

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
