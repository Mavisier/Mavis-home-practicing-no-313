import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.reviews import router as reviews_router
from app.api.runs import router
from app.config import get_settings
from app.db import get_session
from app.schemas import HealthRead

app = FastAPI(title="Agentic Workflow Assistant", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-Demo-Token", "X-Demo-Approver-Token"],
)
app.include_router(router)
app.include_router(reviews_router)
logger = logging.getLogger("workflow")


@app.get("/api/meta")
def metadata():
    settings = get_settings()
    return {
        "generation": settings.llm_provider,
        "embedding": settings.embedding_provider,
        "live_verified": False,
        "photo_analysis": "file_dimensions_and_metadata_only",
    }


@app.exception_handler(SQLAlchemyError)
async def database_error(_request, _exc):
    # Do not log SQL parameters, request text, credentials or connection URLs.
    logger.error("Database operation failed")
    return JSONResponse(status_code=503, content={"detail": "Database temporarily unavailable"})


@app.get("/health", response_model=HealthRead)
def health() -> HealthRead:
    return HealthRead(status="ok")


@app.get("/health/ready", response_model=HealthRead)
def ready(session: Session = Depends(get_session)):
    try:
        extension = session.scalar(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')")
        )
        revision = session.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
        session.execute(text("SELECT id FROM runs LIMIT 0"))
        if not extension or not revision:
            return JSONResponse(status_code=503, content={"status": "unavailable", "milestone": 1})
        return HealthRead(status="ready", database="connected", vector_extension=True)
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "unavailable", "milestone": 1})
