import logging
import structlog

from fastapi import FastAPI
from starlette_exporter import PrometheusMiddleware, handle_metrics

from .config import settings
from .routers.node import router as node_router

# Structured logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ]
)

logging.getLogger("uvicorn").handlers.clear()
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Orbit Explorer – Node API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Prometheus metrics
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)

# Include routers
app.include_router(node_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
        workers=4
    )