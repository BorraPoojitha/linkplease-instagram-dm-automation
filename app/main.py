import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.services.worker import worker
from app.routes import health, rules, webhook, stats, data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB tables & start background worker
    await init_db()
    worker.start()
    yield
    # Shutdown: Stop background worker cleanly
    await worker.stop()


app = FastAPI(
    title="LinkPlease API",
    description="Automated Instagram DM fulfillment for comment keywords.",
    version="1.0.0",
    lifespan=lifespan
)

# Include Routers
app.include_router(health.router)
app.include_router(rules.router)
app.include_router(webhook.router)
app.include_router(stats.router)
app.include_router(data.router)

# Mount Frontend Dist if built
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
