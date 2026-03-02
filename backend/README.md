# Backend - Custom Seven Split

This directory contains the backend application for the Custom Seven Split project, implemented using FastAPI. It automates stock trading strategies, interacts with the Korea Investment & Securities (KIS) API for real-time data and order execution, and manages persistent data using an SQLite database.

## Features

*   **FastAPI Application**: A robust and asynchronous web API built with FastAPI.
*   **KIS API Integration**: Connects to the KIS API for:
    *   Real-time stock price and quote data.
    *   Placing, modifying, and canceling cash orders.
    *   Managing reservation orders (for real investment environments only).
    *   Inquiring account balances and order history.
*   **Seven Split Trading Strategy**: Implements a seven-level stock splitting strategy for automated buying and selling.
*   **Real-time WebSocket Service**: Utilizes KIS WebSocket to receive real-time trade execution notifications and stock quote updates, triggering strategy adjustments.
*   **SQLite Database**: Uses SQLAlchemy ORM to interact with an SQLite database for:
    *   Storing virtual account holdings (`account_db`).
    *   Tracking asset history and cash flow (`asset_history_db`, `cash_flow_db`).
    *   Managing stock monitoring strategies (`stock_strategy_db`).
    *   Recording trade checks (`trade_check_db`).
*   **Scheduled Jobs**: Integrates `APScheduler` for background tasks:
    *   Daily asset snapshots.
    *   Regular refreshing of reservation orders (for real investment environments).
*   **Environment Configuration**: Supports both Virtual (모의투자) and Real (실전투자) KIS API environments, configurable via command-line arguments and `kis_property.yaml`.

## Project Structure

```
backend/
├── app/
│   ├── api/          # FastAPI endpoint definitions (asset, trade strategy, stock)
│   ├── core/         # Core utilities: configuration (config.py), HTTP client (http.py)
│   ├── db/           # Database models (SQLAlchemy), session management, and table creation
│   ├── dto/          # Data Transfer Objects (DTOs) for API request and response bodies
│   ├── lib/          # External library integrations, specifically KIS API client and models
│   │   └── kis/
│   │       ├── client.py   # KIS HTTP and WebSocket client implementations
│   │       └── model.py    # Pydantic models for KIS API requests and responses
│   ├── services/     # Business logic for asset, trade strategy, scheduler, and WebSocket handling
│   └── main.py       # Main FastAPI application entry point, argument parsing, and lifespan events
├── kis_property.yaml # KIS API credentials, account numbers, and token storage
├── sevensplit.db     # SQLite database file (created on startup if not exists)
├── pyproject.toml    # Project configuration and dependencies (ruff for linting/formatting)
├── requirements.txt  # Python dependency list
└── tests/            # Unit tests for various modules
    └── unit/
        └── lib/
            └── kis/  # KIS client unit tests
```

## Setup


### Prerequisites

*   Python 3.9+
*   `pip` or `poetry` for dependency management.

### Installation

1.  **Navigate to the backend directory**:
    ```bash
    cd backend
    ```

2.  **Install dependencies**:
    Using `pip`:
    ```bash
    pip install -r requirements.txt
    ```
    Using `poetry`:
    ```bash
    poetry install
    ```

3.  **KIS API Credentials (`kis_property.yaml`)**:
    Edit the `kis_property.yaml` file in the `backend/` directory. You will need to obtain `app_key`, `app_secret`, and `account` numbers from the Korea Investment & Securities API portal for both virtual and real investment environments.
    ```yaml
    # Example kis_property.yaml content:
    # 실전투자
    real_app_key: "YOUR_REAL_APP_KEY"
    real_app_secret: "YOUR_REAL_APP_SECRET"
    real_account: "YOUR_REAL_ACCOUNT_NUMBER_8_DIGITS"
    real_prod: "01" # 계좌번호 뒤 2자리

    # 모의투자
    virtual_app_key: "YOUR_VIRTUAL_APP_KEY"
    virtual_app_secret: "YOUR_VIRTUAL_APP_SECRET"
    virtual_account: "YOUR_VIRTUAL_ACCOUNT_NUMBER_8_DIGITS"

    # 투자환경 (V & R) - This will be overridden by --env argument if provided
    invest_env: "V"

    # API 토큰 (These will be managed by the application)
    auth_token: ""
    token_type: ""
    expired_time: ""

    # 웹소켓 토큰 (Managed by the application)
    ws_token: ""
    ```
    **Note**: The `auth_token`, `token_type`, `expired_time`, and `ws_token` fields will be automatically managed and updated by the application.

## Running the Application

To start the FastAPI server, navigate to the `backend` directory. The KIS API environment (`V` for Virtual/모의투자, `R` for Real/실전투자) is now configured via the `KIS_ENV` environment variable, which is read within `app/core/config.py`. If `KIS_ENV` is not set, it defaults to `V`.

### 1. Via Command Line

To run the server from your terminal, execute the following command from the `backend` directory:

```bash
KIS_ENV=V python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

*   **`KIS_ENV=V|R`**: Sets the KIS API environment. Replace `V` with `R` for real investment.
*   **`--host 0.0.0.0`**: Makes the server accessible externally (e.g., from a web browser or frontend application).
*   **`--port 8000`**: Specifies the port the server will listen on.
*   **`--reload`**: Enables auto-reloading of the server on code changes, useful for development.

Once running, the API documentation will be available at `http://localhost:8000/docs`.

### 2. Via VS Code Debugger

To run the server in debugging mode using VS Code:

1.  Open the **Run and Debug** view (Ctrl+Shift+D or ⌘⇧D) in VS Code.
2.  Select the **"Python: FastAPI"** configuration from the dropdown menu at the top.
3.  Click the **green play button** to start the server in debug mode.

This configuration (`.vscode/launch.json`) automatically sets the working directory, `PYTHONPATH`, and `KIS_ENV` to `V` (Virtual environment) for convenience. You can modify the `KIS_ENV` in `launch.json` if you wish to debug with the Real environment.

## API Endpoints Overview

The API endpoints are organized under the `/api` prefix, providing a comprehensive set of functionalities for asset management, trading strategy execution, and stock information retrieval.

## API Usage

All API calls should be prefixed with `/api`. For example, to access the total asset endpoint, the full path would be `/api/asset/total`.

### 1. Asset Management (`/api/asset`)

These endpoints provide information about your assets, cash flow, and historical performance.

*   **Get Total Asset**
    *   `GET /api/asset/total`
    *   **Description**: Retrieves the total current asset value, invested capital, profit/loss, and a detailed breakdown of holdings by stock.
    *   **Example Response**:
        ```json
        {
            "예수금": 1000000,
            "투입자본": 5000000,
            "평가금액": 5500000,
            "손익": 500000,
            "stock_dict": {
                "005930": {
                    "투입자본": 3000000,
                    "평가금액": 3300000,
                    "수량": 50,
                    "평균단가": 60000,
                    "손익": 300000
                },
                "035720": {
                    "투입자본": 2000000,
                    "평가금액": 2200000,
                    "수량": 20,
                    "평균단가": 100000,
                    "손익": 200000
                }
            }
        }
        ```

*   **Get Virtual Account Asset**
    *   `GET /api/asset/virtual/{split_level}`
    *   **Description**: Retrieves asset details for a specific virtual account (split level 1-7).
    *   **Path Parameters**:
        *   `split_level` (integer): The virtual account split level (e.g., 1).
    *   **Example Request**: `GET /api/asset/virtual/1`
    *   **Example Response**:
        ```json
        {
            "투입자본": 3000000,
            "평가금액": 3300000,
            "손익": 300000,
            "stock_dict": {
                "005930": {
                    "투입자본": 3000000,
                    "평가금액": 3300000,
                    "수량": 50,
                    "손익": 300000
                }
            }
        }
        ```

*   **Get Cash Flow**
    *   `GET /api/asset/cash-flow`
    *   **Description**: Retrieves cash flow records within a specified date range.
    *   **Query Parameters**:
        *   `start_date` (datetime): Start date for the cash flow inquiry (e.g., `2023-01-01T00:00:00`).
        *   `end_date` (datetime): End date for the cash flow inquiry (e.g., `2023-01-31T23:59:59`).
    *   **Example Request**: `GET /api/asset/cash-flow?start_date=2023-01-01T00:00:00&end_date=2023-01-31T23:59:59`
    *   **Example Response**:
        ```json
        [
            {
                "id": 1,
                "created_at": "2023-01-05T10:00:00",
                "deposit": 1000000,
                "type": "입금",
                "amount": 1000000
            },
            {
                "id": 2,
                "created_at": "2023-01-10T11:30:00",
                "deposit": 700000,
                "type": "매수",
                "amount": -300000
            }
        ]
        ```

*   **Get Asset History**
    *   `GET /api/asset/history`
    *   **Description**: Retrieves historical asset snapshots within a specified date range.
    *   **Query Parameters**:
        *   `start_date` (datetime): Start date for the history inquiry.
        *   `end_date` (datetime): End date for the history inquiry.
    *   **Example Request**: `GET /api/asset/history?start_date=2023-01-01T00:00:00&end_date=2023-01-31T23:59:59`
    *   **Example Response**:
        ```json
        [
            {
                "id": 1,
                "created_at": "2023-01-01T23:59:00",
                "invested_capital": 5000000,
                "total_asset_value": 5100000,
                "cash_balance": 1000000,
                "net_cash_flow": 0,
                "dividend": 0,
                "interest": 0,
                "stock_pnl": 100000,
                "total_pnl": 100000,
                "net_asset_change": 100000
            }
        ]
        ```

### 2. CSS Trade Strategy (`/api/css-trade`)

These endpoints allow you to manage your automated trading strategies.

*   **Create Strategy**
    *   `POST /api/css-trade/strategy`
    *   **Description**: Creates a new Seven Split trading strategy for a given stock. If the market is open, it attempts to place an initial buy order.
    *   **Request Body**:
        ```json
        {
            "stock_code": "005930",
            "invested_capital": 1000000,
            "buy_price": 60000,
            "buy_per": 0.97,
            "first_sell_per": 1.1,
            "sell_per": 1.05
        }
        ```
    *   **Example Response**:
        ```json
        {
            "id": 1,
            "stock_code": "005930",
            "split_level": 1,
            "invested_capital": 1000000,
            "buy_price": 60000,
            "buy_per": 0.97,
            "first_sell_per": 1.1,
            "sell_per": 1.05
        }
        ```

*   **Change Strategy**
    *   `PUT /api/css-trade/strategy/{stock_code}`
    *   **Description**: Modifies an existing trading strategy for a specified stock.
    *   **Path Parameters**:
        *   `stock_code` (string): The stock code of the strategy to modify.
    *   **Request Body (Partial Update)**:
        ```json
        {
            "buy_price": 59000,
            "sell_per": 1.06
        }
        ```
    *   **Example Request**: `PUT /api/css-trade/strategy/005930`
    *   **Example Response**:
        ```json
        {
            "id": 1,
            "stock_code": "005930",
            "split_level": 1,
            "invested_capital": 1000000,
            "buy_price": 59000,
            "buy_per": 0.97,
            "first_sell_per": 1.1,
            "sell_per": 1.06
        }
        ```

*   **Delete Strategy**
    *   `DELETE /api/css-trade/strategy/{stock_code}`
    *   **Description**: Deletes a trading strategy for a specified stock.
    *   **Path Parameters**:
        *   `stock_code` (string): The stock code of the strategy to delete.
    *   **Example Request**: `DELETE /api/css-trade/strategy/005930`
    *   **Example Response**:
        ```json
        true
        ```

*   **Get All Strategies**
    *   `GET /api/css-trade/strategy/all`
    *   **Description**: Retrieves all configured trading strategies.
    *   **Example Response**:
        ```json
        [
            {
                "id": 1,
                "stock_code": "005930",
                "split_level": 1,
                "invested_capital": 1000000,
                "buy_price": 60000,
                "buy_per": 0.97,
                "first_sell_per": 1.1,
                "sell_per": 1.05
            }
        ]
        ```

*   **Get Strategy by Stock Code**
    *   `GET /api/css-trade/strategy/{stock_code}`
    *   **Description**: Retrieves a specific trading strategy by its stock code.
    *   **Path Parameters**:
        *   `stock_code` (string): The stock code of the strategy to retrieve.
    *   **Example Request**: `GET /api/css-trade/strategy/005930`
    *   **Example Response**:
        ```json
        {
            "id": 1,
            "stock_code": "005930",
            "split_level": 1,
            "invested_capital": 1000000,
            "buy_price": 60000,
            "buy_per": 0.97,
            "first_sell_per": 1.1,
            "sell_per": 1.05
        }
        ```

*   **Get Trade Check List**
    *   `GET /api/css-trade/trade-check`
    *   **Description**: Retrieves a list of trade check records based on optional filters.
    *   **Query Parameters (Optional)**:
        *   `stock_code` (string): Filter by stock code.
        *   `status` (integer): Filter by trade status (0=pending, 1=executed, 2=cancelled).
        *   `start_date` (datetime): Start date for the inquiry.
        *   `end_date` (datetime): End date for the inquiry.
    *   **Example Request**: `GET /api/css-trade/trade-check?stock_code=005930&status=0`
    *   **Example Response**:
        ```json
        [
            {
                "trade_id": 1,
                "created_at": "2023-01-10T11:30:00",
                "stock_code": "005930",
                "type": "BUY",
                "price": 60000,
                "count": 10,
                "status": 0
            }
        ]
        ```

### 3. Stock Information & Orders (`/api/stock`)

These endpoints interact directly with stock data and order placement.

*   **Get Current Stock Price**
    *   `GET /api/stock/{stock_code}/price`
    *   **Description**: Retrieves the current price of a specified stock from the KIS API.
    *   **Path Parameters**:
        *   `stock_code` (string): The stock code (e.g., `005930`).
    *   **Example Request**: `GET /api/stock/005930/price`
    *   **Example Response**:
        ```json
        {
            "stock_code": "005930",
            "current_price": 70000
        }
        ```

*   **Place Order**
    *   `POST /api/stock/order`
    *   **Description**: Places a cash order (buy or sell) for a stock via the KIS API.
    *   **Request Body (OrderRequestDto)**:
        ```json
        {
            "stock_code": "005930",
            "quantity": 10,
            "price": 60000,
            "side": "BUY",
            "order_division": "00"
        }
        ```
    *   **Example Response**:
        ```json
        {
            "output": {
                "KRX_FWDG_ORD_ORGNO": "000000",
                "ODNO": "0000000001",
                "ORD_TMD": "103000"
            },
            "rt_cd": "0",
            "msg_cd": "KISA0000",
            "msg1": "정상 처리 되었습니다."
        }
        ```

*   **Modify Order**
    *   `PUT /api/stock/order/modify`
    *   **Description**: Modifies an existing pending order.
    *   **Request Body (ModifyOrderRequestDto)**:
        ```json
        {
            "original_order_no": "0000000001",
            "stock_code": "005930",
            "new_quantity": 15,
            "new_price": 59500,
            "order_division": "00"
        }
        ```
    *   **Example Response**:
        ```json
        {
            "output": {
                "KRX_FWDG_ORD_ORGNO": "000000",
                "ODNO": "0000000002",
                "ORD_TMD": "103500"
            },
            "rt_cd": "0",
            "msg_cd": "KISA0000",
            "msg1": "정상 처리 되었습니다."
        }
        ```

*   **Cancel Order**
    *   `POST /api/stock/order/cancel`
    *   **Description**: Cancels a pending order.
    *   **Request Body (CancelOrderRequestDto)**:
        ```json
        {
            "original_order_no": "0000000001",
            "order_division": "00"
        }
        ```
    *   **Example Response**:
        ```json
        {
            "output": {
                "KRX_FWDG_ORD_ORGNO": "000000",
                "ODNO": "0000000003",
                "ORD_TMD": "104000"
            },
            "rt_cd": "0",
            "msg_cd": "KISA0000",
            "msg1": "정상 처리 되었습니다."
        }
        ```

*   **Get Orders**
    *   `GET /api/stock/orders`
    *   **Description**: Inquires about pending or recently executed orders.
    *   **Query Parameters**:
        *   `order_date` (string): The date of the orders to inquire (YYYYMMDD).
        *   `product_code` (string, Optional): Filter by product code.
    *   **Example Request**: `GET /api/stock/orders?order_date=20230110`
    *   **Example Response**:
        ```json
        {
            "ctx_area_fk100": "",
            "ctx_area_nk100": "",
            "output": [
                {
                    "ord_gno_brno": "0000",
                    "odno": "0000000001",
                    "orgn_odno": "0000000001",
                    "pdno": "005930",
                    "prdt_name": "삼성전자",
                    "rvse_cncl_dvsn_name": "매수",
                    "ord_qty": 10,
                    "ord_unpr": 60000,
                    "ord_tmd": "103000",
                    "tot_ccld_qty": 10,
                    "tot_ccld_amt": 600000,
                    "psbl_qty": 0,
                    "sll_buy_dvsn_cd": "02",
                    "ord_dvsn_cd": "00"
                }
            ],
            "rt_cd": "0",
            "msg_cd": "KISA0000",
            "msg1": "정상 처리 되었습니다."
        }
        ```

*   **Get Stock Info**
    *   `GET /api/stock/{stock_code}/info`
    *   **Description**: Retrieves basic information and current price for a specified stock.
    *   **Path Parameters**:
        *   `stock_code` (string): The stock code.
    *   **Example Request**: `GET /api/stock/005930/info`
    *   **Example Response**:
        ```json
        {
            "stock_code": "005930",
            "current_price": 70000
        }
        ```

## Database

The application uses SQLite, with the database file `sevensplit.db` located in the `backend/` directory. Database tables are automatically created on application startup if they do not already exist.

## WebSocket Service

The `WSService` runs as a background task, connecting to the KIS WebSocket. It subscribes to real-time execution notifications for the configured account and real-time quotes for all stocks in the active trading strategies. This enables immediate reactions to market events.

## Scheduler

The `AsyncIOScheduler` is set up to run two main jobs:
*   `trade_job`: Refreshes reservation orders every 28 days (for real investment environments).
*   `daily_summary_job`: Records a daily snapshot of asset performance at 23:59.
