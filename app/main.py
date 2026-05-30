import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.routers import health, expenses, forecast
from app.services.forecasting import forecasting_service

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # -- Startup -------------------------------------------------------- #
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./data/models", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created")
    forecasting_service.load_model()
    logger.info("Forecasting model load attempted")
    yield
    # -- Shutdown ------------------------------------------------------- #
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered personal expense categorization (LLM) "
        "and next-month forecasting (ML). "
        "Phase 1: data ingestion - Phase 2: AI categorization - Phase 3: ML forecasting."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Routers ------------------------------------------------------------ #
app.include_router(health.router)
app.include_router(expenses.router)
app.include_router(forecast.router)


# -- Global error handler ----------------------------------------------- #
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs."},
    )
