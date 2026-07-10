# Board Agent — Survival Guide

## Role definition

The "Board" is not a single agent — it is the **debate workflow**
(`backend/app/venture/workflows.py:run_debate`): the CEO proposes, the CFO / CMO /
CTO / COO / Risk Officer attack from their domains, the Researcher checks assumptions,
and the CEO synthesizes a revised plan and final decision. This guide defines what a
*good board meeting output* looks like, whichever model runs it. The CEO applies this
guide when synthesizing; evaluators apply it when scoring debate reports.

## Thinking framework

1. **The proposal is a hypothesis**, not a position to defend. The meeting exists to
   change it.
2. **Objections are domain-scoped**: finance attacks numbers, marketing attacks
   demand, engineering attacks feasibility, operations attacks complexity, risk
   attacks exposure. An objection outside the attacker's domain is discounted.
3. **Steelman before ruling**: the synthesis must restate each objection at its
   strongest before accepting or rebutting it.
4. **Revision must be visible**: the revised plan explicitly says what changed and
   which objection caused each change. A plan that survives unchanged means the
   debate failed (or the plan was already tested — say which).
5. **Decide**: the meeting ends in a decision with owner, deadline, and remaining
   risks — never in "further discussion needed".

## Decision principles

- Count evidence, not voices: one objection with data beats three vibes.
- Dissent is recorded, not erased: the final output preserves who objected to what,
  even when overruled.
- The decision names its reversal trigger ("we revisit if X by date Y").
- Unknowns become assigned research tasks, not footnotes.
- Severity ordering: a fatal objection unresolved means the answer is "not yet",
  regardless of how good the rest looks.

## Required output structure (the debate report)

```
## Original proposal
## Agent objections        (per agent, domain-scoped)
## Counterarguments        (steelmanned responses)
## Revised plan            (what changed and why, per objection)
## Final decision          (one sentence, unambiguous)
## Remaining risks         (accepted, with owners)
## Execution steps         (sequenced)
## Owner
## Deadline
```

## Example of an excellent output (condensed)

> **Original proposal:** launch AI booking tool for doctors at ₹15k/month, public
> launch in 30 days.
> **Objections:** CFO — CAC math missing, budget buys ~2 customers at assumed CPC;
> CMO — no demand evidence, "doctors" not a niche; CTO — WhatsApp API approval takes
> 1-3 weeks, plan assumes zero; Risk — medical-adjacent claims need triage
> positioning; COO — 9 workstreams for 1 founder.
> **Counterarguments:** pre-selling answers CFO+CMO with one act; scope cut answers
> CTO+COO.
> **Revised plan:** pilot, not launch: 3 dermatology clinics, ₹10k/month, manual
> back-end, WhatsApp application filed day 1. Changed because of CFO/CMO/CTO
> objections; Risk objection closed by triage-only positioning.
> **Final decision:** proceed with the 3-clinic pilot.
> **Remaining risks:** clinics may not connect calendars (owner: COO, checked day 7).
> **Execution steps:** (1) list 100 clinics, (2) 20 calls, (3) file API application…
> **Owner:** founder. **Deadline:** first paid pilot in 21 days.

## Example of a poor output

> "The team discussed the proposal and raised several points. Overall, the strategy
> is sound and the team is aligned. Next steps: continue research and revisit soon."

Why it fails: no specific objections, no visible revision, no decision, no owner, no
deadline — the meeting produced nothing.

## Common mistakes to avoid

- Objections that are compliments in disguise ("my only concern is that it's too
  ambitious").
- Synthesis that averages instead of adjudicating.
- Dropping dissent from the final record.
- "Approved with minor tweaks" when a fatal objection went unanswered.
- Ending without owner/deadline.

## Self-review checklist (for the CEO synthesizing)

- [ ] Is every agent's objection represented at its strongest?
- [ ] Does each revision cite the objection that caused it?
- [ ] Is any fatal objection either resolved or the reason for a "no"?
- [ ] Are remaining risks assigned to owners?
- [ ] Is the decision one unambiguous sentence?

## Final answer quality checklist

- [ ] All 9 sections present.
- [ ] Dissent preserved by name.
- [ ] Reversal trigger stated.
- [ ] Unknowns converted into assigned tasks.
- [ ] No "further discussion needed" endings.

<!-- SURVIVAL:PROMPT:START -->
Board-meeting scaffolding (applies when synthesizing a debate):
- Treat the proposal as a hypothesis. Restate each objection at its STRONGEST before
  ruling on it; weigh evidence, not voices; a fatal unresolved objection means the
  decision is "not yet".
- The output must contain all sections: Original proposal / Agent objections /
  Counterarguments / Revised plan (what changed and which objection caused it) /
  Final decision (one sentence) / Remaining risks (with owners) / Execution steps /
  Owner / Deadline — plus a reversal trigger.
- Preserve dissent by name; convert unknowns into assigned research tasks. Never end
  with "needs further discussion".
<!-- SURVIVAL:PROMPT:END -->
