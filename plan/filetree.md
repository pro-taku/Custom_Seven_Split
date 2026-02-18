## 6. 디렉토리 구조

```
Custom-Seven-Split/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/          # 라우터 (auth, strategy, trade, dashboard)
│   │   ├── core/                   # 설정 (config, exceptions)
│   │   ├── db/                     # DB 연결 (session)
│   │   ├── models/                 # SQLAlchemy 모델 (schema v3 반영)
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

