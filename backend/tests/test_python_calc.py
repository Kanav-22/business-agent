"""Sandbox tests for python_calc."""
from __future__ import annotations

import pytest

from app.tools.base import ToolError
from app.tools.python_calc import run_python_calc


async def test_basic_math_via_result_variable():
    out = await run_python_calc("result = round(1234.5 * 12, 2)")
    assert "14814.0" in out


async def test_print_output():
    out = await run_python_calc("print(sum(range(10)))")
    assert out.strip() == "45"


async def test_math_and_statistics_importable():
    out = await run_python_calc(
        "import math, statistics\n"
        "result = (math.sqrt(16), statistics.mean([1, 2, 3]))"
    )
    assert "4.0" in out and "2" in out


async def test_forbidden_import_blocked():
    with pytest.raises(ToolError, match="not allowed"):
        await run_python_calc("import os\nresult = os.getcwd()")


async def test_file_access_blocked():
    with pytest.raises(ToolError, match="NameError"):
        await run_python_calc("result = open('/etc/passwd').read()")


async def test_eval_and_dunder_import_blocked():
    with pytest.raises(ToolError, match="NameError"):
        await run_python_calc("result = eval('1+1')")
    with pytest.raises(ToolError, match="not allowed"):
        await run_python_calc("result = __import__('subprocess')")


async def test_infinite_loop_times_out():
    with pytest.raises(ToolError, match="timed out"):
        await run_python_calc("while True:\n    pass", timeout=2.0)


async def test_runtime_error_reported():
    with pytest.raises(ToolError, match="ZeroDivisionError"):
        await run_python_calc("result = 1 / 0")
