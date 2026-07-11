"""FastAPI application: REST endpoints for the dashboard + WebSocket chat
that streams the CEO delegation tree live."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import PlainTextResponse

from pydantic import BaseModel

from app.api.activity import get_activity
from app.api.approvals import AlreadyDecided, decide_approval, list_approvals
from app.api.kpis import get_kpis, get_meta, get_monthly_series
from app.api.reports import get_report, list_reports, save_report
from app.api.venture import (
    archive_memory,
    get_idea,
    get_playbook,
    list_eval_results,
    list_ideas,
    list_memories,
    list_playbooks,
)
from app.config import Settings
from app.data.synthetic import SyntheticProvider
from app.db import make_engine
from app.scheduler import JOBS, create_scheduler
from app.venture.founder import get_founder_profile, set_founder_profile
from app.venture.router import route as route_request
from app.venture.workflows import VENTURE_WORKFLOWS

log = logging.getLogger("business-agent")

MAX_HISTORY_MESSAGES = 8


class DecisionBody(BaseModel):
    """Optional note accompanying an approve/reject decision."""

    note: str | None = None


class RouteBody(BaseModel):
    """A free-text request for the prompt router."""

    message: str


class FounderBody(BaseModel):
    """Founder profile update: any subset of the 16 documented keys."""

    values: dict[str, str]


class WorkflowBody(BaseModel):
    """Topic supplied to a venture workflow."""

    topic: str


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
        scheduler = None
        if settings.scheduler_enabled:
            scheduler = create_scheduler(service, engine)
            scheduler.start()
            log.info(
                "Scheduler started: %s",
                ", ".join(str(j) for j in scheduler.get_jobs()),
            )
        yield
        if scheduler is not None:
            scheduler.shutdown(wait=False)

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
        return {"status": "ok", "mode": "demo" if settings.demo_mode else "live"}

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
        finance = {a.config.name for a in service.finance_team.values()}
        venture = {a.config.name for a in service.venture_team.values()}

        def team(name: str) -> str | None:
            if name in finance:
                return "finance"
            if name in venture:
                return "venture"
            return None

        return [
            {
                "name": a.config.name,
                "display_name": a.config.display_name,
                "description": a.config.description,
                "color": a.config.color,
                "tools": a.config.tools,
                "team": team(a.config.name),
            }
            for a in service.all_agents()
        ]

    # ------------------------------------------------------------- reports

    @app.get("/api/reports")
    def reports(kind: str | None = None, limit: int = 50):
        return list_reports(engine, kind=kind, limit=max(1, min(limit, 200)))

    @app.get("/api/reports/{report_id}")
    def report_detail(report_id: int):
        report = get_report(engine, report_id)
        if report is None:
            raise HTTPException(status_code=404, detail="report not found")
        return report

    @app.get("/api/reports/{report_id}/download")
    def report_download(report_id: int):
        report = get_report(engine, report_id)
        if report is None:
            raise HTTPException(status_code=404, detail="report not found")
        filename = f"report-{report_id}.md"
        return PlainTextResponse(
            report["content"],
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/briefing")
    def latest_briefing():
        briefings = list_reports(engine, kind="briefing", limit=1)
        if not briefings:
            return {"report": None}
        return {"report": get_report(engine, briefings[0]["id"])}

    # ------------------------------------------------------------ approvals

    @app.get("/api/approvals")
    def approvals(status: str | None = None, limit: int = 100):
        if status not in (None, "pending", "approved", "rejected"):
            raise HTTPException(status_code=400, detail="invalid status filter")
        return list_approvals(engine, status=status, limit=max(1, min(limit, 200)))

    def _decide(approval_id: int, approve: bool, body: DecisionBody | None):
        try:
            decided = decide_approval(
                engine, approval_id, approve=approve, note=body.note if body else None
            )
        except AlreadyDecided as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        if decided is None:
            raise HTTPException(status_code=404, detail="approval not found")
        return decided

    @app.post("/api/approvals/{approval_id}/approve")
    def approve(approval_id: int, body: DecisionBody | None = None):
        decided = _decide(approval_id, True, body)
        # Approval is the moment content becomes an artifact: publish it to
        # the reports library (kind='content'), our stand-in for "external".
        report_id = save_report(
            engine,
            title=decided["title"],
            content=decided["content"],
            agent=decided["agent"],
            kind="content",
        )
        return {**decided, "published_report_id": report_id}

    @app.post("/api/approvals/{approval_id}/reject")
    def reject(approval_id: int, body: DecisionBody | None = None):
        return _decide(approval_id, False, body)

    # ---------------------------------------------------------------- jobs

    jobs_in_flight: set[str] = set()

    @app.post("/api/jobs/{job_name}/run", status_code=202)
    async def run_job(job_name: str):
        job = JOBS.get(job_name)
        if job is None:
            raise HTTPException(status_code=404, detail=f"unknown job {job_name!r}")
        if job_name in jobs_in_flight:
            raise HTTPException(status_code=409, detail=f"{job_name} is already running")

        async def runner():
            try:
                await job(service, engine)
            except Exception:
                log.exception("job %s failed", job_name)
            finally:
                jobs_in_flight.discard(job_name)

        jobs_in_flight.add(job_name)
        asyncio.get_running_loop().create_task(runner())
        return {"started": True, "job": job_name}

    # ---------------------------------------------------------- venture layer

    venture_tasks: set[asyncio.Task] = set()

    @app.get("/api/venture/workflows")
    def venture_workflows():
        return [
            {
                "name": name,
                "label": workflow["label"],
                "description": workflow["description"],
            }
            for name, workflow in VENTURE_WORKFLOWS.items()
        ]

    @app.post("/api/venture/{workflow_name}", status_code=202)
    async def run_venture_workflow(workflow_name: str, body: WorkflowBody):
        workflow = VENTURE_WORKFLOWS.get(workflow_name)
        if workflow is None:
            raise HTTPException(
                status_code=404,
                detail=f"unknown venture workflow {workflow_name!r}",
            )
        topic = (body.topic or "").strip()
        if not topic:
            raise HTTPException(status_code=400, detail="topic is required")
        if len(topic) > 500:
            raise HTTPException(
                status_code=400,
                detail="topic must be at most 500 characters",
            )

        job_key = f"venture:{workflow_name}"
        if job_key in jobs_in_flight:
            raise HTTPException(
                status_code=409,
                detail=f"{workflow_name} is already running",
            )

        async def runner():
            try:
                await workflow["run"](service, engine, topic)
            except Exception:
                log.exception("venture workflow %s failed", workflow_name)
            finally:
                jobs_in_flight.discard(job_key)

        jobs_in_flight.add(job_key)
        task = asyncio.get_running_loop().create_task(runner())
        venture_tasks.add(task)
        task.add_done_callback(venture_tasks.discard)
        return {"started": True, "workflow": workflow_name}

    @app.post("/api/route")
    def route_endpoint(body: RouteBody):
        message = (body.message or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        return route_request(message, engine).to_dict()

    @app.get("/api/founder")
    def founder():
        return get_founder_profile(engine)

    @app.put("/api/founder")
    def update_founder(body: FounderBody):
        try:
            return set_founder_profile(engine, body.values)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/memories")
    def memories(
        category: str | None = None,
        status: str = "active",
        related_idea: str | None = None,
        limit: int = 100,
    ):
        if status not in ("active", "archived", ""):
            raise HTTPException(status_code=400, detail="invalid status filter")
        return list_memories(
            engine,
            category=category,
            status=status,
            related_idea=related_idea,
            limit=max(1, min(limit, 200)),
        )

    @app.post("/api/memories/{memory_id}/archive")
    def memory_archive(memory_id: int):
        if not archive_memory(engine, memory_id):
            raise HTTPException(status_code=404, detail="memory not found")
        return {"archived": True, "id": memory_id}

    @app.get("/api/ideas")
    def ideas(limit: int = 50):
        return list_ideas(engine, limit=max(1, min(limit, 200)))

    @app.get("/api/ideas/{idea_id}")
    def idea_detail(idea_id: int):
        idea = get_idea(engine, idea_id)
        if idea is None:
            raise HTTPException(status_code=404, detail="idea not found")
        return idea

    @app.get("/api/playbooks")
    def playbooks():
        return list_playbooks()

    @app.get("/api/playbooks/{slug}")
    def playbook_detail(slug: str):
        playbook = get_playbook(slug)
        if playbook is None:
            raise HTTPException(status_code=404, detail="playbook not found")
        return playbook

    @app.get("/api/evals")
    def evals(agent: str | None = None, limit: int = 200):
        return list_eval_results(engine, agent=agent, limit=max(1, min(limit, 500)))

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
                                "credentials, set ANTHROPIC_API_KEY — or set "
                                "DEMO_MODE=1 for a zero-cost demo — and restart "
                                "the backend."
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
