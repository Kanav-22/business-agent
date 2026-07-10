"""Phase 2: parallel fan-out, new specialists, validated writes, server tools,
pause_turn resumption, activity feed."""
from __future__ import annotations

import shutil

from sqlalchemy import text

from app.agents.service import AgentService
from app.api.activity import get_activity
from app.db import make_engine
from app.tools.base import ToolError
from app.tools.create_task import validate_and_create_task
from tests.fake_anthropic import FakeClient, response, text_block, tool_use_block


def make_service(settings, responses) -> tuple[AgentService, FakeClient]:
    fake = FakeClient(responses)
    return AgentService(settings, client_factory=lambda: fake), fake


async def collect_events(service, message):
    events = []

    async def on_event(event):
        events.append(event)

    result, budget = await service.ask_ceo(message, on_event=on_event)
    return result, budget, events


def test_roster_has_five_specialists(settings):
    service, _ = make_service(settings, [])
    assert set(service.specialists) == {"cfo", "cmo", "cto", "researcher", "coordinator"}
    # least privilege: each specialist only sees its own tables
    cmo_doc = service.specialists["cmo"].registry.schemas(["sql_query"])[0]["description"]
    assert "campaigns(" in cmo_doc and "invoices(" not in cmo_doc
    cto_doc = service.specialists["cto"].registry.schemas(["sql_query"])[0]["description"]
    assert "projects(" in cto_doc and "campaigns(" not in cto_doc


async def test_parallel_fan_out_to_three_specialists(settings):
    responses = {
        "CEO orchestrator": [
            response(
                [
                    tool_use_block("tu_cfo", "delegate_to_agent",
                                   {"agent": "cfo", "task": "Summarize the P&L."}),
                    tool_use_block("tu_cmo", "delegate_to_agent",
                                   {"agent": "cmo", "task": "Best channel by CAC?"}),
                    tool_use_block("tu_cto", "delegate_to_agent",
                                   {"agent": "cto", "task": "Any at-risk projects?"}),
                ],
                stop_reason="tool_use",
            ),
            response([text_block("Per the CFO… The CMO reports… Per the CTO…")]),
        ],
        "CFO agent": [
            response(
                [tool_use_block("tu_1", "sql_query",
                                {"query": "SELECT SUM(amount) FROM transactions WHERE type='revenue'"})],
                stop_reason="tool_use",
            ),
            response([text_block("Revenue summarized.")]),
        ],
        "CMO agent": [
            response(
                [tool_use_block("tu_2", "sql_query",
                                {"query": "SELECT channel, SUM(spend)/SUM(conversions) AS cac "
                                          "FROM campaigns GROUP BY channel ORDER BY cac LIMIT 1"})],
                stop_reason="tool_use",
            ),
            response([text_block("Best CAC channel found.")]),
        ],
        "CTO agent": [
            response(
                [tool_use_block("tu_3", "sql_query",
                                {"query": "SELECT name FROM projects WHERE status='at_risk'"})],
                stop_reason="tool_use",
            ),
            response([text_block("Two projects are at risk.")]),
        ],
    }
    service, fake = make_service(settings, responses)
    result, budget, events = await collect_events(service, "How's the business doing?")

    assert result.error is None
    # three specialist runs, all parented under the CEO's run
    starts = [e for e in events if e["type"] == "run_started"]
    assert [s["agent"] for s in starts if s["depth"] == 0] == ["ceo"]
    ceo_run = starts[0]["run_id"]
    children = [s for s in starts if s["depth"] == 1]
    assert {s["agent"] for s in children} == {"cfo", "cmo", "cto"}
    assert all(s["parent_run_id"] == ceo_run for s in children)

    # every specialist ran a real query against its own allowlist
    specialist_results = [
        e for e in events
        if e["type"] == "tool_result" and e["agent"] in {"cfo", "cmo", "cto"}
    ]
    assert len(specialist_results) == 3
    assert not any(e["is_error"] for e in specialist_results)

    # all three delegation results returned to the CEO in ONE user message,
    # in the same order the tool_use blocks were emitted
    final_ceo_call = fake.calls[-1]
    last_user = final_ceo_call["messages"][-1]
    ids = [entry["tool_use_id"] for entry in last_user["content"]]
    assert ids == ["tu_cfo", "tu_cmo", "tu_cto"]

    assert set(budget.by_agent) == {"ceo", "cfo", "cmo", "cto"}


async def test_coordinator_creates_validated_task(settings, tmp_path):
    # copy the seeded DB so the write does not leak into other tests
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    settings.db_path = db_copy

    responses = {
        "CEO orchestrator": [
            response(
                [tool_use_block("tu_1", "delegate_to_agent",
                                {"agent": "coordinator",
                                 "task": "Create a task to renew the SOC 2 audit contract."})],
                stop_reason="tool_use",
            ),
            response([text_block("The Coordinator created the task.")]),
        ],
        "Workflow Coordinator": [
            response(
                [tool_use_block("tu_2", "create_task",
                                {"title": "Renew SOC 2 audit contract",
                                 "department": "Operations",
                                 "status": "open"})],
                stop_reason="tool_use",
            ),
            response([text_block("Created the task.")]),
        ],
    }
    service, _ = make_service(settings, responses)
    result, _, events = await collect_events(service, "Add a task to renew the SOC 2 contract")

    assert result.error is None
    created = next(
        e for e in events if e["type"] == "tool_result" and e["tool"] == "create_task"
    )
    assert not created["is_error"]
    assert "Created task #" in created["output"]

    engine = make_engine(db_copy)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT department, status FROM tasks WHERE title = 'Renew SOC 2 audit contract'")
        ).one()
    assert tuple(row) == ("Operations", "open")


def test_create_task_validation_rejects_bad_input(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    engine = make_engine(db_copy)

    import pytest

    with pytest.raises(ToolError, match="department"):
        validate_and_create_task(engine, {"title": "x", "department": "Sales"})
    with pytest.raises(ToolError, match="status"):
        validate_and_create_task(engine, {"title": "x", "department": "Marketing", "status": "done"})
    with pytest.raises(ToolError, match="blocked_reason"):
        validate_and_create_task(engine, {"title": "x", "department": "Marketing", "status": "blocked"})
    with pytest.raises(ToolError, match="due_date"):
        validate_and_create_task(
            engine, {"title": "x", "department": "Marketing", "due_date": "next week"}
        )
    with pytest.raises(ToolError, match="No employee"):
        validate_and_create_task(
            engine, {"title": "x", "department": "Marketing", "assignee_name": "Nobody Real"}
        )
    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM tasks WHERE title = 'x'")).scalar_one()
    assert n == 0


async def test_researcher_declares_server_web_tools(settings):
    responses = {"Researcher agent": [response([text_block("Competitors charge $99-$500.")])]}
    service, fake = make_service(settings, responses)
    researcher = service.specialists["researcher"]

    async def on_event(event):
        pass

    from app.agents.budget import TokenBudget

    result = await researcher.run(
        "What do competitors charge?",
        on_event=on_event,
        budget=TokenBudget(limit=10_000),
    )
    assert result.error is None
    tools = fake.calls[0]["tools"]
    types = {t.get("type") for t in tools}
    assert "web_search_20260209" in types and "web_fetch_20260209" in types
    # CMO gets web_search only; CFO gets no server tools
    assert any(t["type"] == "web_search_20260209" for t in service.specialists["cmo"].config.server_tools)
    assert service.specialists["cfo"].config.server_tools == []


async def test_pause_turn_resumes_without_tool_results(settings):
    responses = {
        "Researcher agent": [
            response([text_block("Searching…")], stop_reason="pause_turn"),
            response([text_block("Done: competitors charge $99-$500.")]),
        ]
    }
    service, fake = make_service(settings, responses)

    async def on_event(event):
        pass

    from app.agents.budget import TokenBudget

    result = await service.specialists["researcher"].run(
        "Scan competitor pricing",
        on_event=on_event,
        budget=TokenBudget(limit=10_000),
    )
    assert result.error is None
    assert "Done" in result.output
    # second call resumed with the assistant turn appended, no tool_result message
    second = fake.calls[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant"]


async def test_activity_feed_built_from_logs(settings):
    responses = {
        "CEO orchestrator": [
            response(
                [tool_use_block("tu_1", "delegate_to_agent",
                                {"agent": "cfo", "task": "Count customers"})],
                stop_reason="tool_use",
            ),
            response([text_block("Per the CFO: counted.")]),
        ],
        "CFO agent": [
            response(
                [tool_use_block("tu_2", "sql_query", {"query": "SELECT COUNT(*) FROM customers"})],
                stop_reason="tool_use",
            ),
            response([text_block("Counted.")]),
        ],
    }
    service, _ = make_service(settings, responses)
    result, _, _ = await collect_events(service, "how many customers?")
    assert result.error is None

    runs = get_activity(settings.logs_dir, limit=10)
    assert len(runs) == 2
    by_agent = {r["agent"]: r for r in runs}
    assert by_agent["ceo"]["status"] == "completed"
    assert by_agent["ceo"]["tools"] == [{"tool": "delegate_to_agent", "count": 1}]
    assert by_agent["cfo"]["parent_run_id"] == by_agent["ceo"]["run_id"]
    assert by_agent["cfo"]["tools"] == [{"tool": "sql_query", "count": 1}]
    # per-run usage and cost are populated (2 scripted calls each: 240 in / 120 out)
    assert by_agent["cfo"]["input_tokens"] == 240
    assert by_agent["cfo"]["output_tokens"] == 120
    assert by_agent["cfo"]["cost_usd"] > 0
    # newest first
    assert runs[0]["started_at"] >= runs[1]["started_at"]
