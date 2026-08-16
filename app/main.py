import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
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

# Enable CORS for cross-origin frontend communication (e.g. Vercel frontend calling Render backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router)
app.include_router(rules.router)
app.include_router(webhook.router)
app.include_router(stats.router)
app.include_router(data.router)

# Path to frontend dist
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

@app.get("/", include_in_schema=False)
async def root():
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return RedirectResponse(url="/docs")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
