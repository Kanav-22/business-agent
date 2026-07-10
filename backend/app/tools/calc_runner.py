"""Subprocess entrypoint for python_calc. Runs UNTRUSTED, model-written code.

Invoked as: python -I calc_runner.py   (code arrives on stdin)

Defense layers (in addition to the parent's wall-clock timeout):
- separate process, isolated mode (-I): no site-packages, no env vars honored
- rlimits: CPU seconds and address space
- restricted builtins: no open/exec/eval/compile/input, and __import__ only
  resolves 'math' and 'statistics'
If the executed code sets a variable named `result`, it is printed last.
"""
from __future__ import annotations

import sys

ALLOWED_MODULES = ("math", "statistics")


def _limited_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split(".")[0] in ALLOWED_MODULES:
        return __import__(name, globals, locals, fromlist, level)
    raise ImportError(f"import of {name!r} is not allowed; only {ALLOWED_MODULES} are available")


_SAFE_BUILTIN_NAMES = [
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float",
    "format", "frozenset", "int", "isinstance", "issubclass", "iter", "len", "list",
    "map", "max", "min", "next", "pow", "print", "range", "repr", "reversed", "round",
    "set", "slice", "sorted", "str", "sum", "tuple", "zip",
    "ArithmeticError", "Exception", "IndexError", "KeyError", "OverflowError",
    "StopIteration", "TypeError", "ValueError", "ZeroDivisionError",
]


def main() -> int:
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    except Exception:
        pass  # non-POSIX fallback: parent timeout still applies

    code = sys.stdin.read()
    import builtins

    safe_builtins = {name: getattr(builtins, name) for name in _SAFE_BUILTIN_NAMES}
    safe_builtins["__import__"] = _limited_import
    import math
    import statistics

    globs = {"__builtins__": safe_builtins, "math": math, "statistics": statistics}
    try:
        exec(compile(code, "<python_calc>", "exec"), globs)
    except BaseException as exc:  # noqa: BLE001 — report everything to the agent
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if "result" in globs:
        print(repr(globs["result"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
