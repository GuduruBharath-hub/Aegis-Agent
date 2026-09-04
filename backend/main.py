from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.errors import install_error_handlers
from backend.api.routes_benchmarks import router as benchmarks_router
from backend.api.routes_demo import router as demo_router
from backend.api.routes_jobs import router as jobs_router
from backend.api.routes_replay import router as replay_router
from backend.api.runtime import ApiRuntime


def create_app(runtime: ApiRuntime | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owns_runtime = runtime is None
        active_runtime = runtime or ApiRuntime.build_default()
        app.state.runtime = active_runtime
        try:
            yield
        finally:
            if owns_runtime:
                await active_runtime.close()

    app = FastAPI(
        title="AegisAgent API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )
    install_error_handlers(app)
    app.include_router(jobs_router)
    app.include_router(demo_router)
    app.include_router(benchmarks_router)
    app.include_router(replay_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
