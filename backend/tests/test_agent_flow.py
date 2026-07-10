"""End-to-end agent-loop tests with a scripted model client. Tool execution
is real (sql_query runs against the seeded DB); only the LLM is scripted."""
from __future__ import annotations

import json

from app.agents.service import AgentService
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


async def test_ceo_delegates_through_cfo_to_fpa(settings):
    """The Phase 3 org chart: CEO → CFO (finance orchestrator) → FP&A → SQL."""
    responses = {
        "CEO orchestrator": [
            response(
                [
                    text_block("Let me pull that from the CFO."),
                    tool_use_block("tu_1", "delegate_to_agent",
                                   {"agent": "cfo", "task": "How many active customers?"}),
                ],
                stop_reason="tool_use",
            ),
            response([text_block("Per the CFO: see active customer count above.")]),
        ],
        "You are the CFO": [
            response(
                [tool_use_block("tu_2", "delegate_to_agent",
                                {"agent": "fpa", "task": "Count active customers."})],
                stop_reason="tool_use",
            ),
            response([text_block("Per FP&A: counted from the customers table.")]),
        ],
        "FP&A agent": [
            response(
                [tool_use_block("tu_3", "sql_query",
                                {"query": "SELECT COUNT(*) AS n FROM customers WHERE churn_date IS NULL"})],
                stop_reason="tool_use",
            ),
            response([text_block("We have the queried number of active customers.")]),
        ],
    }
    service, fake = make_service(settings, responses)
    result, budget, events = await collect_events(service, "How many customers do we have?")

    assert result.error is None
    assert "Per the CFO" in result.output

    kinds = [(e["type"], e["agent"]) for e in events]
    assert kinds == [
        ("run_started", "ceo"),
        ("agent_text", "ceo"),
        ("tool_call", "ceo"),          # delegate_to_agent → cfo
        ("run_started", "cfo"),
        ("tool_call", "cfo"),          # delegate_to_agent → fpa
        ("run_started", "fpa"),
        ("tool_call", "fpa"),          # sql_query
        ("tool_result", "fpa"),
        ("agent_text", "fpa"),
        ("run_completed", "fpa"),
        ("tool_result", "cfo"),
        ("agent_text", "cfo"),
        ("run_completed", "cfo"),
        ("tool_result", "ceo"),
        ("agent_text", "ceo"),
        ("run_completed", "ceo"),
    ]

    # parenting: ceo(0) → cfo(1) → fpa(2)
    ceo_run = events[0]["run_id"]
    cfo_started = next(e for e in events if e["type"] == "run_started" and e["agent"] == "cfo")
    fpa_started = next(e for e in events if e["type"] == "run_started" and e["agent"] == "fpa")
    assert cfo_started["parent_run_id"] == ceo_run and cfo_started["depth"] == 1
    assert fpa_started["parent_run_id"] == cfo_started["run_id"] and fpa_started["depth"] == 2

    # real sql result flowed back through the delegation chain
    sql_result = next(e for e in events if e["type"] == "tool_result" and e["agent"] == "fpa")
    assert not sql_result["is_error"]
    assert any(ch.isdigit() for ch in sql_result["output"])

    # token accounting: 6 scripted calls x (120 in + 60 out)
    assert budget.input_tokens == 6 * 120
    assert budget.output_tokens == 6 * 60
    assert set(budget.by_agent) == {"ceo", "cfo", "fpa"}

    # least privilege at every level
    assert all(c["model"] == settings.agent_model for c in fake.calls)
    tools_by_system = {
        c["system"][:30]: {t["name"] for t in c["tools"]} for c in fake.calls
    }
    for prefix, tools in tools_by_system.items():
        if "CEO" in prefix:
            assert tools == {"get_agent_roster", "delegate_to_agent"}
        elif "CFO" in prefix:
            assert tools == {"delegate_to_agent"}
        elif "FP&A" in prefix:
            assert tools == {"sql_query", "python_calc"}


async def test_decisions_are_logged_as_jsonl(settings):
    responses = [response([text_block("Hello! Ask me about the business.")])]
    service, _ = make_service(settings, responses)
    result, _, _ = await collect_events(service, "hi")
    assert result.error is None

    log_files = list(settings.logs_dir.glob("decisions-*.jsonl"))
    assert len(log_files) == 1
    records = [json.loads(line) for line in log_files[0].read_text().splitlines()]
    types = [r["type"] for r in records]
    assert "chat_request" in types
    assert "run_started" in types
    assert "run_completed" in types
    completed = next(r for r in records if r["type"] == "run_completed")
    assert completed["agent"] == "ceo"
    assert completed["usage"]["output_tokens"] > 0


async def test_delegation_depth_limit(settings):
    settings.max_delegation_depth = 0
    responses = [
        response(
            [tool_use_block("tu_1", "delegate_to_agent", {"agent": "cfo", "task": "profit?"})],
            stop_reason="tool_use",
        ),
        response([text_block("I could not delegate.")]),
    ]
    service, fake = make_service(settings, responses)
    result, _, events = await collect_events(service, "what was profit?")

    refusal = next(e for e in events if e["type"] == "tool_result" and e["agent"] == "ceo")
    assert "Delegation refused" in refusal["output"]
    # CFO never ran — only the two CEO calls were consumed
    assert len(fake.calls) == 2
    assert not any(e["agent"] == "cfo" for e in events)
    assert result.error is None


async def test_unknown_agent_delegation_fails_gracefully(settings):
    responses = [
        response(
            [tool_use_block("tu_1", "delegate_to_agent",
                            {"agent": "legal", "task": "Review the MSA."})],
            stop_reason="tool_use",
        ),
        response([text_block("We have no legal specialist on the roster.")]),
    ]
    service, _ = make_service(settings, responses)
    result, _, events = await collect_events(service, "can legal review the MSA?")
    failure = next(e for e in events if e["type"] == "tool_result")
    assert "no agent named 'legal'" in failure["output"]
    assert result.error is None


async def test_token_budget_aborts_run(settings):
    settings.token_budget = 100  # first call (180 tokens) blows through it
    responses = [
        response([text_block("thinking...")], stop_reason="tool_use"),
        response([text_block("never reached")]),
    ]
    service, fake = make_service(settings, responses)
    result, budget, events = await collect_events(service, "expensive question")

    assert result.error == "budget_exceeded"
    assert len(fake.calls) == 1
    completed = next(e for e in events if e["type"] == "run_completed")
    assert completed["error"] == "budget_exceeded"
