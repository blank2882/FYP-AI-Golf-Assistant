from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import router
from app.core import config
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    # Configure logging first so startup messages and errors are visible in the console.
    configure_logging()
    # Create required upload/output folders before serving requests.
    config.ensure_directories()

    # FastAPI app object is the entry point for routes and middleware.
    app = FastAPI(title="FYP AI Golf Assistant")

    # Register all API and HTML endpoints from the router module.
    app.include_router(router)

    # Expose static folders so browser clients can load CSS/JS and generated media files.
    app.mount("/static", StaticFiles(directory=str(config.APP_DIR / "static")), name="static")
    app.mount("/outputs", StaticFiles(directory=str(config.OUTPUTS_DIR)), name="outputs")
    app.mount("/uploads", StaticFiles(directory=str(config.UPLOADS_DIR)), name="uploads")

    return app


app = create_app()
