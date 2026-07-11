"""Deterministic venture orchestration: agents think; code sequences, validates,
and persists their work.

The workflows call venture agents directly rather than routing through chat so
their order, concurrency, report structure, and memory writes remain explicit.
"""
from __future__ import annotations

import asyncio

from sqlalchemy.engine import Engine

from app.agents.budget import TokenBudget
from app.api.reports import save_report
from app.api.venture import (
    get_idea,
    list_ideas,
    memory_context,
    save_memory_record,
)
from app.venture.founder import founder_context
from app.venture.scoring import VERDICT_LABELS, render_scoreboard


async def _noop_event(event: dict) -> None:
    return None


def _brief(topic: str, instructions: str, engine: Engine) -> str:
    """Build a workflow brief with the demo-mode topic marker first."""
    parts = [f"TOPIC: {topic}\n{instructions.strip()}"]
    founder = founder_context(engine)
    memories = memory_context(engine, limit=8)
    if founder:
        parts.append(founder)
    if memories:
        parts.append(memories)
    return "\n\n".join(parts)


async def _run(service, agent_name: str, task: str, budget, on_event) -> str:
    """Run one workflow agent and turn any agent failure into report content."""
    display_name = agent_name.removeprefix("venture_").replace("_", " ").title()
    try:
        roster = (
            service.specialists if agent_name == "researcher" else service.venture_team
        )
        agent = roster[agent_name]
        display_name = agent.config.display_name
        result = await agent.run(task, on_event=on_event, budget=budget)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        return f"[{display_name} unavailable: {error}]"
    if result.error:
        return f"[{display_name} unavailable: {result.error}]"
    return result.output


async def run_debate(service, engine, topic: str, *, on_event=None) -> int:
    """Run a proposal, parallel board critique, evidence check, and revision."""
    topic = topic.strip()
    budget = TokenBudget(limit=service.settings.token_budget)
    event_sink = on_event or _noop_event

    proposal = await _run(
        service,
        "venture_ceo",
        _brief(
            topic,
            "Propose a strategy for this topic. State the niche, offer, price, "
            "channel, key numbers, numbered assumptions, and first three steps.",
            engine,
        ),
        budget,
        event_sink,
    )

    critique_specs = [
        (
            "venture_cfo",
            "Attack the proposal's financial assumptions, cash timing, costs, "
            "revenue logic, and runway.",
        ),
        (
            "venture_cmo",
            "Attack the proposal's demand, positioning, target customer, and "
            "acquisition-channel assumptions.",
        ),
        (
            "venture_cto",
            "Attack the proposal's technical feasibility, estimates, dependencies, "
            "and fallback assumptions.",
        ),
        (
            "coo",
            "Attack the proposal's execution complexity, capacity assumptions, "
            "lead times, ownership, and sequencing.",
        ),
        (
            "risk",
            "Attack the proposal's legal, regulatory, financial-exposure, and "
            "reputational assumptions.",
        ),
    ]
    objections = await asyncio.gather(
        *(
            _run(
                service,
                agent_name,
                _brief(
                    topic,
                    f"{instruction}\n\nPROPOSAL TO ATTACK:\n{proposal}",
                    engine,
                ),
                budget,
                event_sink,
            )
            for agent_name, instruction in critique_specs
        )
    )
    cfo, cmo, cto, coo, risk = objections

    research = await _run(
        service,
        "researcher",
        _brief(
            topic,
            "Check the proposal's numbered assumptions. Identify what evidence "
            "supports or contradicts each one, cite sources when available, and "
            f"mark what remains unverified.\n\nPROPOSAL:\n{proposal}",
            engine,
        ),
        budget,
        event_sink,
    )

    objection_block = (
        f"CFO:\n{cfo}\n\n"
        f"CMO:\n{cmo}\n\n"
        f"CTO:\n{cto}\n\n"
        f"COO:\n{coo}\n\n"
        f"Risk Officer:\n{risk}"
    )
    revision = await _run(
        service,
        "venture_ceo",
        _brief(
            topic,
            "Revise the original proposal after weighing every one of the objections "
            "below and the research check. State what changed, make one final "
            "decision, preserve remaining dissent, and give execution steps with "
            "owners and deadlines.\n\n"
            f"ORIGINAL PROPOSAL:\n{proposal}\n\n"
            f"BOARD OBJECTIONS:\n{objection_block}\n\n"
            f"RESEARCHER ASSUMPTION CHECK:\n{research}",
            engine,
        ),
        budget,
        event_sink,
    )

    content = (
        f"## Original proposal\n\n{proposal}\n\n"
        "## Agent objections\n\n"
        f"### CFO\n\n{cfo}\n\n"
        f"### CMO\n\n{cmo}\n\n"
        f"### CTO\n\n{cto}\n\n"
        f"### COO\n\n{coo}\n\n"
        f"### Risk Officer\n\n{risk}\n\n"
        f"## Researcher — assumption check\n\n{research}\n\n"
        f"## Counterarguments & revision\n\n{revision}\n"
    )
    report_id = save_report(
        engine,
        title=f"Board debate: {topic[:150]}",
        content=content,
        agent="venture_ceo",
        kind="debate",
    )
    save_memory_record(
        engine,
        category="decision",
        title=f"Debate decision: {topic}"[:200],
        content=f"{revision[:1500]} Full report: #{report_id}.",
        source_agent="venture_ceo",
        related_idea=topic[:80],
    )
    return report_id


async def run_failure_simulation(service, engine, topic: str, *, on_event=None) -> int:
    """Run parallel adversarial and risk-oriented failure simulations."""
    topic = topic.strip()
    budget = TokenBudget(limit=service.settings.token_budget)
    event_sink = on_event or _noop_event
    instructions = (
        "Simulate how this could fail after 7 days, 30 days, 90 days, and 1 year. "
        "For every failure mode include: failure mode, cause, early warning signs, "
        "probability (L/M/H), damage level, prevention plan, recovery plan, and the "
        "agent responsible. Rank the most dangerous failures first."
    )
    red_team, risk = await asyncio.gather(
        _run(
            service,
            "red_team",
            _brief(topic, instructions, engine),
            budget,
            event_sink,
        ),
        _run(
            service,
            "risk",
            _brief(topic, instructions, engine),
            budget,
            event_sink,
        ),
    )
    content = (
        f"## Red team — failure modes\n\n{red_team}\n\n"
        f"## Risk officer — exposure\n\n{risk}\n\n"
        "## How to use this\n\n"
        "Turn each prevention plan into an owned task with a deadline before the "
        "corresponding risk window. Add the early-warning signs to weekly checks so "
        "the team can intervene before damage compounds.\n"
    )
    report_id = save_report(
        engine,
        title=f"Failure simulation: {topic}",
        content=content,
        agent="red_team",
        kind="failure_sim",
    )
    save_memory_record(
        engine,
        category="risk",
        title=f"Failure modes: {topic}"[:200],
        content=f"{red_team[:1500]} Full report: #{report_id}.",
        source_agent="red_team",
        related_idea=topic[:80],
    )
    return report_id


async def run_customer_interviews(service, engine, topic: str, *, on_event=None) -> int:
    """Generate a synthetic customer panel and retain its synthesis."""
    topic = topic.strip()
    budget = TokenBudget(limit=service.settings.token_budget)
    event_sink = on_event or _noop_event
    interview_output = await _run(
        service,
        "interviewer",
        _brief(
            topic,
            "Generate exactly 20 diverse synthetic personas. For each include "
            "customer type, background, current problem, current solution, "
            "frustration level, budget, buying trigger, objections, exact words, "
            "most-valued feature, ignored feature, likelihood to buy, and best "
            "message angle. Then synthesize common pains, objections, strongest "
            "and weakest segments, offer, niche, pricing, landing-page message, "
            "and three real-world validation steps.",
            engine,
        ),
        budget,
        event_sink,
    )
    disclaimer = (
        "**These are synthetic interviews, not real customer evidence; validate "
        "the findings with real customers before acting on them.**"
    )
    content = f"{disclaimer}\n\n{interview_output}\n"
    report_id = save_report(
        engine,
        title=f"Synthetic interviews: {topic}",
        content=content,
        agent="interviewer",
        kind="interviews",
    )
    synthesis_at = interview_output.lower().find("synthesis")
    memory_content = (
        interview_output[synthesis_at:]
        if synthesis_at >= 0
        else interview_output[:1500]
    )
    save_memory_record(
        engine,
        category="customer_research",
        title=f"Synthetic interviews: {topic}"[:200],
        content=memory_content,
        source_agent="interviewer",
        related_idea=topic[:80],
    )
    return report_id


async def run_idea_score(service, engine, topic: str, *, on_event=None) -> int:
    """Run strict scoring and render the deterministically persisted idea."""
    topic = topic.strip()
    budget = TokenBudget(limit=service.settings.token_budget)
    event_sink = on_event or _noop_event
    before = list_ideas(engine, limit=1)
    previous_id = before[0]["id"] if before else None
    scored_idea_ids: list[int] = []

    async def score_event(event: dict) -> None:
        if (
            event.get("type") == "tool_result"
            and event.get("tool") == "score_idea"
            and not event.get("is_error")
        ):
            output = str(event.get("output") or "")
            marker = "Idea #"
            marker_at = output.find(marker)
            if marker_at >= 0:
                id_text = output[marker_at + len(marker) :].split(maxsplit=1)[0]
                if id_text.isdigit() and int(id_text) not in scored_idea_ids:
                    scored_idea_ids.append(int(id_text))
        await event_sink(event)

    scorer_output = await _run(
        service,
        "scorer",
        _brief(
            topic,
            "Score this idea strictly across all 14 fixed categories. Call the "
            "score_idea tool exactly once with complete rationales, the best "
            "version, worst risk, cheapest validation test, and three next actions.",
            engine,
        ),
        budget,
        score_event,
    )
    newest = list_ideas(engine, limit=1)
    newest_id = newest[0]["id"] if newest else None
    idea = None
    if len(scored_idea_ids) == 1 and scored_idea_ids[0] != previous_id:
        idea = get_idea(engine, scored_idea_ids[0])

    if idea is None:
        attribution_note = ""
        if newest_id != previous_id:
            attribution_note = (
                " A new idea row exists, but it could not be safely attributed to "
                "this workflow run."
            )
        content = (
            "## Result\n\n"
            "No idea was scored because the scorer did not persist exactly one "
            f"attributable idea.{attribution_note}\n\n"
            f"## Scorer output\n\n{scorer_output}\n"
        )
        return save_report(
            engine,
            title=f"Idea score: {topic}",
            content=content,
            agent="scorer",
            kind="idea_score",
        )

    score_payload = idea["scores"]
    scores = {key: value["score"] for key, value in score_payload.items()}
    rationales = {
        key: value["rationale"] for key, value in score_payload.items()
    }
    verdict = VERDICT_LABELS[idea["verdict"]]
    scoreboard = render_scoreboard(scores, rationales)
    content = (
        f"## Result\n\n**Total score:** {idea['total_score']}/10  \n"
        f"**Verdict:** {verdict}\n\n"
        f"## Scoreboard\n\n{scoreboard}\n\n"
        f"## Best version\n\n{idea['best_version']}\n\n"
        f"## Worst risk\n\n{idea['worst_risk']}\n\n"
        f"## Cheapest validation test\n\n{idea['validation_test']}\n\n"
        f"## Next actions\n\n{idea['next_actions']}\n\n"
        f"## Scorer closing\n\n{scorer_output}\n"
    )
    return save_report(
        engine,
        title=f"Idea score: {idea['title']}",
        content=content,
        agent="scorer",
        kind="idea_score",
    )


VENTURE_WORKFLOWS: dict[str, dict] = {
    "debate": {
        "run": run_debate,
        "label": "Board debate",
        "description": (
            "CEO proposes; CFO/CMO/CTO/COO/Risk attack; researcher checks; "
            "CEO decides."
        ),
    },
    "failure_sim": {
        "run": run_failure_simulation,
        "label": "Failure simulation",
        "description": (
            "Red Team and Risk Officer model failure horizons, warning signs, "
            "prevention, and recovery."
        ),
    },
    "interviews": {
        "run": run_customer_interviews,
        "label": "Synthetic customer interviews",
        "description": (
            "Interviewer generates 20 synthetic personas and a validation-focused "
            "customer synthesis."
        ),
    },
    "idea_score": {
        "run": run_idea_score,
        "label": "Idea score",
        "description": (
            "Idea Scorer proposes strict category scores; deterministic code "
            "computes and persists the verdict."
        ),
    },
}
