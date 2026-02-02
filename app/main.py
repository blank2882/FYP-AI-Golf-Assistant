from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import router
from app.core import config
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    config.ensure_directories()

    app = FastAPI(title="FYP AI Golf Assistant")

    app.include_router(router)

    app.mount("/static", StaticFiles(directory=str(config.APP_DIR / "static")), name="static")
    app.mount("/outputs", StaticFiles(directory=str(config.OUTPUTS_DIR)), name="outputs")
    app.mount("/uploads", StaticFiles(directory=str(config.UPLOADS_DIR)), name="uploads")

    return app


app = create_app()
