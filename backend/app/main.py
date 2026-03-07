import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.logger import logger
from requests import Session

# Now, import modules using their full path from the 'backend' root
from app.api import api_router
from app.core.config import GLOBAL_ENV
from app.core.websocket import CSSWebSocket
from app.db.session import Base, SessionLocal, engine
from app.lib.kis.client import KISWsClient
from app.lib.kis.model import RealtimeExecutionResponse, RealtimeQuoteResponse
from app.services.css_trade_service import CSSTradeService

# Ensure the 'backend' directory is in the Python path.
# This makes 'app' discoverable as a subpackage of 'backend'.
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, os.pardir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger.info(f"Running in KIS environment: {GLOBAL_ENV}")

# Global WebSocket client instance for KIS data
kis_realtime_ws: Optional[CSSWebSocket] = None
kis_ws_client_instance: Optional[KISWsClient] = None

# Base API router for "/" endpoints
root_router = APIRouter()


@root_router.get("/")
async def root():
    return {
        "message": "Welcome to Custom Seven Split API",
        "environment": GLOBAL_ENV,
    }


# Lifespan context for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    global kis_realtime_ws, kis_ws_client_instance
    # Startup events
    logger.info("Application startup begins.")

    # 1. Create DB tables if they don't exist
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables checked/created.")

    # 2. Initialize KIS WebSocket client
    kis_ws_client_instance = KISWsClient(env=GLOBAL_ENV)
    await kis_ws_client_instance.load_websocket_approval_key()
    logger.info("KIS WebSocket approval key loaded.")

    # 3. Initialize generic WebSocket client (CSSWebSocket)
    kis_realtime_ws = CSSWebSocket(
        ws_url=f"{kis_ws_client_instance.ws_domain}/tryitout/H0STCNI0",
    )

    # 4. Define KIS-specific message handler for CSSWebSocket
    async def kis_message_handler(message: str):
        if not kis_ws_client_instance:
            logger.error("KISWsClient instance is not available in message handler.")
            return

        header, parsed_response = kis_ws_client_instance._process_websocket_message(
            message,
        )

        if not parsed_response:
            if header.get("tr_id") == "PINGPONG":
                logger.debug("Received KIS PINGPONG message.")
            return

        if isinstance(parsed_response, RealtimeExecutionResponse):
            trade_type_raw = parsed_response.output.trade_type
            trade_type = (
                "SELL"
                if trade_type_raw == "1"
                else "BUY"
                if trade_type_raw == "2"
                else None
            )

            if trade_type and parsed_response.output.ccld_qty > 0:
                stock_code = parsed_response.output.iscd
                ccld_prc = parsed_response.output.ccld_prc
                ccld_qty = parsed_response.output.ccld_qty

                logger.info(
                    f"[KIS WS] Execution: {trade_type} {ccld_qty} of {stock_code} @ {ccld_prc}",
                )

                db: Session = SessionLocal()
                try:
                    css_trade_service = CSSTradeService(db)
                    await css_trade_service.check_trade_result(
                        stock_code=stock_code,
                        trade_type=trade_type,
                        execution_price=ccld_prc,
                        execution_qty=ccld_qty,
                    )
                except Exception as e:
                    logger.error(
                        f"Error handling KIS trade result for {stock_code}: {e}",
                        exc_info=True,
                    )
                finally:
                    db.close()

        elif isinstance(parsed_response, RealtimeQuoteResponse):
            stock_code = parsed_response.tr_key
            current_price = parsed_response.output.stck_prpr
            # Update latest price (if still needed, or rely solely on subscribers)
            # kis_realtime_ws.latest_prices[stock_code] = current_price # CSSWebSocket doesn't have this
            logger.debug(f"[KIS WS] Realtime Quote: {stock_code} - {current_price}")
            # Publish to internal FastAPI WebSocket clients
            await kis_realtime_ws.publish_to_subscribers(
                stock_code,
                parsed_response.output.model_dump(),
            )

    # # 5. Subscribe to initial strategies from DB (if any) using CSSWebSocket
    # db: Session = SessionLocal()
    # try:
    #     strategies = StockStrategyDB.get_all(db)
    #     for strategy in strategies:
    #         stock_code = strategy.stock_code
    #         # Construct KIS-specific subscription message
    #         kis_subscribe_msg = kis_ws_client_instance.subscribe_realtime_quote(
    #             stock_code,
    #         )
    #         kis_unsubscribe_msg = kis_ws_client_instance.unsubscribe_realtime_data(
    #             tr_id=TR.TR_KS_RT_PRICE_R.value,
    #             tr_key=stock_code,
    #             tr_type="2",
    #         )
    #         # Use a dummy queue for initial DB-based subscriptions as they don't have a direct client connection yet
    #         # The CSSWebSocket will send the server_subscribe_message when its connection is established
    #         await kis_realtime_ws.subscribe_client(
    #             topic=stock_code,
    #             client_queue=asyncio.Queue(),  # Dummy queue, as no direct FastAPI client yet
    #             server_subscribe_message=kis_subscribe_msg,
    #             server_unsubscribe_message=kis_unsubscribe_msg,
    #         )
    #         logger.info(f"Queued initial KIS subscription for {stock_code} from DB.")
    # finally:
    #     db.close()

    # 6. Start the generic WebSocket client in a background task with the KIS message handler
    asyncio.create_task(kis_realtime_ws.start(kis_message_handler))
    logger.info("WebSocket service initiated.")

    yield

    # Shutdown events
    logger.info("Application shutdown begins.")
    # Stop WebSocket service
    if kis_realtime_ws:
        await kis_realtime_ws.stop()
    logger.info("WebSocket service stopped.")
    logger.info("Application shutdown completed.")


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Include API routers
app.include_router(root_router)
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, port=8000)
