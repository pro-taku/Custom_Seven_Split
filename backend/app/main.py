import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

# Ensure the 'backend' directory is in the Python path.
# This makes 'app' discoverable as a subpackage of 'backend'.
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, os.pardir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uvicorn
from fastapi import APIRouter, FastAPI

# Now, import modules using their full path from the 'backend' root
from app.api import api_router
from app.db.session import Base, engine
from app.services.ws_service import ws_service_instance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Parse command-line arguments
from app.core.config import GLOBAL_ENV

logger.info(f"Running in KIS environment: {GLOBAL_ENV}")

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
    # Startup events
    logger.info("Application startup begins.")

    # 1. Create DB tables if they don't exist
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables checked/created.")

    # 2. Initialize WebSocket service in a background task, passing the environment
    ws_service_instance.initialize(GLOBAL_ENV)
    asyncio.create_task(ws_service_instance.start())
    logger.info("WebSocket service initiated.")

    yield

    # Shutdown events
    logger.info("Application shutdown begins.")
    # Stop WebSocket service
    await ws_service_instance.stop()
    logger.info("WebSocket service stopped.")
    logger.info("Application shutdown completed.")


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Include API routers
app.include_router(root_router)
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, port=8000)
