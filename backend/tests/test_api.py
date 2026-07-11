"""REST + WebSocket API tests (FastAPI TestClient, scripted model client)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.service import AgentService
from app.main import create_app
from tests.fake_anthropic import FakeClient, response, text_block, tool_use_block


def make_client(settings, responses) -> TestClient:
    service = AgentService(settings, client_factory=lambda: FakeClient(responses))
    app = create_app(settings=settings, service=service)
    return TestClient(app)


def test_kpis_endpoint(settings):
    with make_client(settings, []) as client:
        res = client.get("/api/kpis")
        assert res.status_code == 200
        body = res.json()
        assert body["company"] == "Lumina Labs"
        assert body["mrr"] > 0
        assert body["active_customers"] > 0
        assert body["cash"] > 0
        assert body["open_tasks"] > 0


def test_chart_endpoint(settings):
    with make_client(settings, []) as client:
        res = client.get("/api/chart/revenue-expenses")
        assert res.status_code == 200
        series = res.json()
        assert len(series) == 18
        assert {"month", "revenue", "expenses", "profit"} <= set(series[0])


def test_agents_endpoint(settings):
    with make_client(settings, []) as client:
        agents = client.get("/api/agents").json()
        names = {a["name"] for a in agents}
        # The original operations roster must always be present…
        assert names >= {
            "ceo", "cfo", "cmo", "cto", "researcher", "coordinator",
            "fpa", "reporting", "revenue", "control", "content",
        }
        finance = {a["name"] for a in agents if a["team"] == "finance"}
        assert finance == {"fpa", "reporting", "revenue", "control"}
        # …and the venture layer is listed as its own team.
        venture = {a["name"] for a in agents if a["team"] == "venture"}
        assert venture == {
            "venture_ceo", "venture_cfo", "venture_cmo", "venture_cto",
            "coo", "risk", "red_team", "sales", "interviewer", "scorer",
        }


def test_chat_websocket_streams_delegation(settings):
    responses = [
        response(
            [tool_use_block("tu_1", "delegate_to_agent",
                            {"agent": "cto", "task": "Which projects are at risk?"})],
            stop_reason="tool_use",
        ),
        response(
            [tool_use_block("tu_2", "sql_query",
                            {"query": "SELECT name, deadline FROM projects "
                                      "WHERE status = 'at_risk'"})],
            stop_reason="tool_use",
        ),
        response([text_block("Two projects are at risk; see query above.")]),
        response([text_block("Per the CTO, two projects are currently at risk.")]),
    ]
    with make_client(settings, responses) as client:
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"message": "what was revenue last month?"})
            events = []
            while True:
                event = ws.receive_json()
                events.append(event)
                if event["type"] == "done":
                    break

    types = [e["type"] for e in events]
    assert types.count("run_started") == 2  # ceo + cto
    assert "tool_call" in types and "tool_result" in types
    done = events[-1]
    assert done["error"] is None
    assert done["usage"]["total"] == 4 * 180
    agents_seen = {e.get("agent") for e in events if "agent" in e}
    assert {"ceo", "cto"} <= agents_seen


def test_chat_websocket_reports_empty_message(settings):
    with make_client(settings, []) as client:
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"message": "   "})
            event = ws.receive_json()
            assert event["type"] == "error"
