"""
api/main.py

FastAPI application entry point.
- CORS configured for Vite dev server (localhost:5173)
- Mounts all routers under /api prefix
- Serves React static build in production (if frontend/dist exists)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routers import query, graph, patients, arxiv, stats

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Medical GraphRAG API",
    description=(
        "REST API for the Medical Knowledge GraphRAG system. "
        "Provides endpoints for hybrid graph+vector medical queries, "
        "patient profiles, knowledge graph visualisation, and arXiv research."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # CRA fallback
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(query.router,    prefix="/api")
app.include_router(graph.router,    prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(arxiv.router,    prefix="/api")
app.include_router(stats.router,    prefix="/api")

# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "Medical GraphRAG API"}

# ── Serve React static files in production ────────────────────────────────────

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_react_app(full_path: str):
        """Catch-all: serve React index.html for client-side routing."""
        index = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return {"error": "Frontend not built. Run `npm run build` in frontend/"}
