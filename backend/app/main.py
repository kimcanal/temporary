"""SlotLock FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import admin, auth, reservations, spaces
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.scripts.seed import seed_if_empty

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("slotlock")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    # Ensure btree_gist for exclusion constraint
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        Base.metadata.create_all(bind=conn)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    logger.info("SlotLock ready (debug=%s)", settings.debug)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Study-room reservation MVP – no double-booking under concurrency (EXCLUDE USING gist).",
        lifespan=lifespan,
    )
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix="/api")
    app.include_router(spaces.router, prefix="/api")
    app.include_router(reservations.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "slotlock"}

    return app


app = create_app()
