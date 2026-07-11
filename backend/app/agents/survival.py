"""Model Downgrade Survival Kit — runtime half.

When SURVIVAL_MODE=1, the scaffolding block of each agent's survival guide
(docs/survival/*.md, between the SURVIVAL:PROMPT markers) is appended to that
agent's system prompt at construction time. Weaker models keep the thinking
framework, output structure and self-checks that a stronger model infers on
its own. Off by default: prompts are byte-identical to the pre-survival build.

The guides are the source of truth — edit them, not this file. Missing guides
or markers degrade silently to "no suffix" so a docs problem can never break
agent construction."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.config import BACKEND_ROOT

SURVIVAL_DIR = BACKEND_ROOT.parent / "docs" / "survival"

# agent name -> guide file. venture_* critics share the matching C-suite guide;
# the venture strategist uses the BOARD guide (its output IS the board format).
GUIDE_FOR_AGENT = {
    "ceo": "CEO_AGENT_SURVIVAL_GUIDE.md",
    "cfo": "CFO_AGENT_SURVIVAL_GUIDE.md",
    "cmo": "CMO_AGENT_SURVIVAL_GUIDE.md",
    "cto": "CTO_AGENT_SURVIVAL_GUIDE.md",
    "coo": "COO_AGENT_SURVIVAL_GUIDE.md",
    "researcher": "RESEARCH_AGENT_SURVIVAL_GUIDE.md",
    "sales": "SALES_AGENT_SURVIVAL_GUIDE.md",
    "risk": "RISK_AGENT_SURVIVAL_GUIDE.md",
    "venture_ceo": "BOARD_AGENT_SURVIVAL_GUIDE.md",
    "venture_cfo": "CFO_AGENT_SURVIVAL_GUIDE.md",
    "venture_cmo": "CMO_AGENT_SURVIVAL_GUIDE.md",
    "venture_cto": "CTO_AGENT_SURVIVAL_GUIDE.md",
}

_BLOCK_RE = re.compile(
    r"<!--\s*SURVIVAL:PROMPT:START\s*-->\s*(.*?)\s*<!--\s*SURVIVAL:PROMPT:END\s*-->",
    re.DOTALL,
)


@lru_cache(maxsize=None)
def survival_suffix(agent_name: str) -> str:
    """The guide's injectable block for this agent, or '' when unavailable."""
    filename = GUIDE_FOR_AGENT.get(agent_name)
    if filename is None:
        return ""
    path = SURVIVAL_DIR / filename
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = _BLOCK_RE.search(text)
    return match.group(1).strip() if match else ""


def apply_survival(agent_name: str, system_prompt: str, *, enabled: bool) -> str:
    """Append the survival scaffolding when enabled. The original prompt stays
    the prefix, so demo-mode marker matching is unaffected."""
    if not enabled:
        return system_prompt
    suffix = survival_suffix(agent_name)
    if not suffix:
        return system_prompt
    return f"{system_prompt}\n\n{suffix}"
