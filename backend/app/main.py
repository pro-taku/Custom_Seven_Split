from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import engine
from app.models import base
from app.api.endpoints import strategy, asset, settings
from app.services.scheduler import setup_scheduler

# 앱 모듈이 처음 import 됐을 때, DB와 테이블이 없으면 새로 만든다.
base.Base.metadata.create_all(bind=engine)

# 앱의 생명주기에 따라 실행할 함수 (비동기)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Setup scheduler
    scheduler = setup_scheduler()
    yield
    # Shutdown: Stop scheduler
    scheduler.shutdown()

app = FastAPI(
    title="Custom Seven Split API",
    description="API for automating the Seven Split investment strategy.",
    version="0.1.0",
    lifespan=lifespan
)

# Include Routers
app.include_router(strategy.router, prefix="/api/strategy", tags=["Strategy"])
app.include_router(asset.router, prefix="/api/asset", tags=["Asset"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])

@app.get("/", tags=["Root"])
def read_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Welcome to the Custom Seven Split API!"}
