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


async def test_ceo_delegates_to_cfo_and_synthesizes(settings):
    responses = [
        # 1. CEO decides to delegate
        response(
            [
                text_block("Let me pull that from the CFO."),
                tool_use_block("tu_1", "delegate_to_agent",
                               {"agent": "cfo", "task": "How many customers do we have?"}),
            ],
            stop_reason="tool_use",
        ),
        # 2. CFO queries the database (REAL sql_query execution)
        response(
            [tool_use_block("tu_2", "sql_query",
                            {"query": "SELECT COUNT(*) AS n FROM customers WHERE churn_date IS NULL"})],
            stop_reason="tool_use",
        ),
        # 3. CFO answers
        response([text_block("We have the queried number of active customers.")]),
        # 4. CEO synthesizes
        response([text_block("Per the CFO: see active customer count above.")]),
    ]
    service, fake = make_service(settings, responses)
    result, budget, events = await collect_events(service, "How many customers do we have?")

    assert result.error is None
    assert "Per the CFO" in result.output

    kinds = [(e["type"], e["agent"]) for e in events]
    assert kinds == [
        ("run_started", "ceo"),
        ("agent_text", "ceo"),
        ("tool_call", "ceo"),          # delegate_to_agent
        ("run_started", "cfo"),
        ("tool_call", "cfo"),          # sql_query
        ("tool_result", "cfo"),
        ("agent_text", "cfo"),
        ("run_completed", "cfo"),
        ("tool_result", "ceo"),        # delegation result back to CEO
        ("agent_text", "ceo"),
        ("run_completed", "ceo"),
    ]

    # the CFO's run is correctly parented under the CEO's run
    ceo_run = events[0]["run_id"]
    cfo_started = next(e for e in events if e["type"] == "run_started" and e["agent"] == "cfo")
    assert cfo_started["parent_run_id"] == ceo_run
    assert cfo_started["depth"] == 1

    # real sql result flowed back through the delegation
    sql_result = next(e for e in events if e["type"] == "tool_result" and e["agent"] == "cfo")
    assert not sql_result["is_error"]
    assert any(ch.isdigit() for ch in sql_result["output"])

    # token accounting: 4 scripted calls x (120 in + 60 out)
    assert budget.input_tokens == 4 * 120
    assert budget.output_tokens == 4 * 60
    assert set(budget.by_agent) == {"ceo", "cfo"}

    # all four API calls used the configured model; CFO got only its own tools
    assert all(c["model"] == settings.agent_model for c in fake.calls)
    cfo_call_tools = {t["name"] for t in fake.calls[1]["tools"]}
    assert cfo_call_tools == {"sql_query", "python_calc"}
    ceo_call_tools = {t["name"] for t in fake.calls[0]["tools"]}
    assert ceo_call_tools == {"get_agent_roster", "delegate_to_agent"}


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
