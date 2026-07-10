"""Sandboxed numeric computation tool. Executes model-written code in a
separate, resource-limited process (see calc_runner.py)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from app.tools.base import Tool, ToolError

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.base import ToolContext

_RUNNER = Path(__file__).with_name("calc_runner.py")
_MAX_OUTPUT_CHARS = 4000

PYTHON_CALC_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": (
                "Python code for numeric computation. print() what you need, or assign "
                "the final value to a variable named `result`. Only `math` and "
                "`statistics` may be imported; no files, no network, no other imports."
            ),
        }
    },
    "required": ["code"],
}


async def run_python_calc(code: str, *, timeout: float = 6.0) -> str:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-I", str(_RUNNER),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(code.encode()), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise ToolError(f"Computation timed out after {timeout:.0f}s.")
    out = stdout.decode(errors="replace").strip()
    err = stderr.decode(errors="replace").strip()
    if proc.returncode != 0:
        raise ToolError(err or "Computation failed.")
    if len(out) > _MAX_OUTPUT_CHARS:
        out = out[:_MAX_OUTPUT_CHARS] + "\n…(output truncated)"
    return out or "(no output — print() a value or assign to `result`)"


def make_python_calc_tool(*, timeout: float = 6.0) -> Tool:
    async def handler(tool_input: dict, ctx: "ToolContext") -> str:
        code = tool_input.get("code", "")
        if not code.strip():
            raise ToolError("Empty code.")
        return await run_python_calc(code, timeout=timeout)

    return Tool(
        name="python_calc",
        description=(
            "Run sandboxed Python for numeric computation (growth rates, runway math, "
            "averages…). print() intermediate values or assign the final answer to "
            "`result`. Only the `math` and `statistics` modules are importable; there "
            "is no file, network, or database access — fetch data with sql_query first."
        ),
        input_schema=PYTHON_CALC_SCHEMA,
        handler=handler,
    )
