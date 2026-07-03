"""EvidenceOS Mini FastAPI application."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.routes import benchmarks, documents, qa, reports


def create_app() -> FastAPI:
    app = FastAPI(
        title="EvidenceOS Mini API",
        description="Audit-ready document intelligence for regulated workflows.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(documents.router)
    app.include_router(qa.router)
    app.include_router(reports.router)
    app.include_router(benchmarks.router)
    return app


app = create_app()
