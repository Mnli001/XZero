"""Project Zero API gateway."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import websocket
from .api.routes_backtest import router as backtest_router
from .api.routes_execution import router as execution_router
from .api.routes_health import router as health_router
from .api.routes_journal import router as journal_router
from .api.routes_knowledge import router as knowledge_router
from .api.routes_market import router as market_router
from .api.routes_risk import router as risk_router
from .api.routes_strategies import router as strategies_router
from .config import settings
from .database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Project Zero API", version="0.1.0",
              description="AI-powered SMC/ICT order-flow terminal. All risk gates enforced server-side.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_origins == "*" else [o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

for r in (health_router, market_router, backtest_router, strategies_router,
          risk_router, execution_router, journal_router, knowledge_router):
    app.include_router(r, prefix="/api")

app.include_router(websocket.router)


@app.get("/")
def root():
    return {"app": "project-zero", "docs": "/docs",
            "note": "Dashboard runs separately (Next.js). This is the API + compute core."}
