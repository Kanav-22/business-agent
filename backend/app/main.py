"""FastAPI application: REST endpoints for the dashboard + WebSocket chat
that streams the CEO delegation tree live."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.activity import get_activity
from app.api.kpis import get_kpis, get_meta, get_monthly_series
from app.config import Settings
from app.data.synthetic import SyntheticProvider
from app.db import make_engine

log = logging.getLogger("business-agent")

MAX_HISTORY_MESSAGES = 8


def create_app(settings: Settings | None = None, service=None) -> FastAPI:
    settings = settings or Settings.from_env()
    engine = make_engine(settings.db_path)

    if service is None:
        from app.agents.service import AgentService

        service = AgentService(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        summary = SyntheticProvider(seed=settings.data_seed).provision(engine)
        if not summary.get("skipped"):
            log.info("Seeded synthetic data: %s", summary)
        yield

    app = FastAPI(title="AI Business OS", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.agent_service = service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ----------------------------------------------------------------- REST

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/meta")
    def meta():
        return get_meta(engine)

    @app.get("/api/kpis")
    def kpis():
        return get_kpis(engine)

    @app.get("/api/chart/revenue-expenses")
    def revenue_expenses():
        return get_monthly_series(engine)

    @app.get("/api/activity")
    def activity(limit: int = 50):
        return get_activity(
            settings.logs_dir,
            limit=max(1, min(limit, 200)),
            input_price_per_mtok=settings.input_price_per_mtok,
            output_price_per_mtok=settings.output_price_per_mtok,
        )

    @app.get("/api/agents")
    def agents():
        roster = [service.ceo, *service.specialists.values()]
        return [
            {
                "name": a.config.name,
                "display_name": a.config.display_name,
                "description": a.config.description,
                "color": a.config.color,
                "tools": a.config.tools,
            }
            for a in roster
        ]

    # ------------------------------------------------------------- WebSocket

    @app.websocket("/ws/chat")
    async def chat(ws: WebSocket):
        await ws.accept()
        history: list[dict] = []
        # Parallel delegation emits events concurrently; serialize the socket.
        send_lock = asyncio.Lock()
        try:
            while True:
                payload = await ws.receive_json()
                message = (payload.get("message") or "").strip()
                if not message:
                    await ws.send_json({"type": "error", "message": "Empty message."})
                    continue

                async def on_event(event: dict) -> None:
                    async with send_lock:
                        await ws.send_json(event)

                try:
                    result, budget = await service.ask_ceo(
                        message, on_event=on_event, history=history
                    )
                except WebSocketDisconnect:
                    raise
                except Exception as exc:  # e.g. missing ANTHROPIC_API_KEY
                    log.exception("chat request failed")
                    await ws.send_json(
                        {
                            "type": "error",
                            "message": (
                                f"{type(exc).__name__}: {exc}. If this mentions "
                                "credentials, set ANTHROPIC_API_KEY and restart the backend."
                            ),
                        }
                    )
                    continue

                if not result.error:
                    history.append({"role": "user", "content": message})
                    history.append({"role": "assistant", "content": result.output or "…"})
                    del history[:-MAX_HISTORY_MESSAGES]
                await ws.send_json(
                    {
                        "type": "done",
                        "run_id": result.run_id,
                        "error": result.error,
                        "usage": budget.snapshot(),
                        "duration_ms": result.duration_ms,
                    }
                )
        except WebSocketDisconnect:
            pass

    return app


app = create_app()
