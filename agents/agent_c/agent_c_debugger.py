"""
Agent C: Tester & Debugger  --  Week 3 deliverable (debugger).

Pipeline position:
    Agent B (implementation_output.json)
        -> Agent C tester  (test_output.json: tests + sandbox failures)   <-- INPUT
            -> Agent C debugger (debug_output.json: analysis + fix)        <-- OUTPUT (this module)

Week 3 scope (per roadmap):
    "Build debugger -- input: failing tests + code -> output: bug analysis + fix."

This module:
  1. Consumes the structured `failures` list that the Week 2 sandbox runner
     already produces (test nodeid, outcome, traceback_summary).
  2. Categorizes each failure by root-cause type from the traceback
     (AssertionError / ImportError / TypeError / AttributeError /
      NameError / IndexError|KeyError / runtime error / collection error).
  3. Produces a human-readable bug analysis per failure.
  4. Builds a Qwen "repair" prompt (code + failing tests + tracebacks) and
     asks for a corrected version of the code-under-test, with a deterministic
     mock fixer as a fallback -- mirroring Agent B's (M3) mock-fallback design
     so the pipeline never crashes without an API key / network.
  5. Runs the fix-verify step by re-testing the fixed code in the same
     subprocess sandbox, and reports whether the fix closed the failures.

It reuses Week 2's sandbox runner and ast-based generator from
agent_c_tester.py rather than re-implementing them.
"""

import ast
import json
import os
import re
import sys
import time
from types import SimpleNamespace

# Reuse Week 2 building blocks. Import works whether this module is run as a
# package (agents.agent_c.agent_c_debugger, e.g. from the orchestrator or
# pytest) or directly from inside the agent_c/ folder.
try:
    # Preferred canonical path: the runner now lives in the sandbox package
    # (M5 Week 4). It routes Docker-first with a subprocess fallback.
    from sandbox.sandbox_runner import run_tests_in_sandbox
except ImportError:  # running directly from inside agents/agent_c/ (repo root not on path)
    from agent_c_tester import run_tests_in_sandbox

try:
    from agents.agent_c.agent_c_tester import (
        extract_code_from_text,
        patch_missing_imports,
        _DASHSCOPE_AVAILABLE,
    )
except ImportError:  # running directly from inside agents/agent_c/
    from agent_c_tester import (
        extract_code_from_text,
        patch_missing_imports,
        _DASHSCOPE_AVAILABLE,
    )

try:
    from dotenv import load_dotenv
    import dashscope
except Exception:  # pragma: no cover - optional dependency
    pass

try:
    from llm.logging_ import log_call as _log_call
except ImportError:
    _log_call = None


# --------------------------------------------------------------------------- #
# 1. Traceback categorization (root-cause analysis)                           #
# --------------------------------------------------------------------------- #
# Ordered: more specific patterns first. Each entry maps a regex against the
# traceback summary to a (category, default_explanation) pair.
_CATEGORY_RULES = [
    ("collection_error", r"errors during collection|ERROR collecting",
     "pytest could not even import/collect the test module. Usually a bad "
     "import name or a syntax error in the code under test."),
    ("ImportError", r"\b(ImportError|ModuleNotFoundError)\b",
     "The test imports a name or module that does not exist. Check the class "
     "name and that the module filename matches the import."),
    ("AttributeError", r"\bAttributeError\b",
     "The code calls a method/attribute that the class does not define. The "
     "method name in the implementation likely differs from what tests expect."),
    ("TypeError", r"\bTypeError\b",
     "A function was called with the wrong number/type of arguments, or a "
     "return value was used incorrectly (e.g. unpacking a non-tuple)."),
    ("NameError", r"\bNameError\b",
     "A name is used before it is defined -- often a typo or a missing import "
     "inside the code under test."),
    ("KeyError", r"\bKeyError\b",
     "A dictionary lookup used a key that is not present -- often a missing "
     "existence check before access."),
    ("IndexError", r"\bIndexError\b",
     "A sequence was indexed out of range."),
    ("AssertionError", r"\bAssertionError\b|\bassert\b",
     "The code ran but produced a value the test did not expect. This is a "
     "logic bug: the behavior is wrong, not the syntax."),
]


def categorize_failure(traceback_summary):
    """Return (category, explanation) for one failure's traceback text."""
    text = traceback_summary or ""
    for category, pattern, explanation in _CATEGORY_RULES:
        if re.search(pattern, text):
            return category, explanation
    return "runtime_error", (
        "The test raised an exception at runtime that does not match a known "
        "category. Inspect the traceback for the raised exception type."
    )


def analyze_failures(failures):
    """
    Turn the sandbox `failures` list into structured bug analysis.
    Input items: {test, outcome, traceback_summary}.
    Output items add: {category, explanation}.
    """
    analyzed = []
    for f in failures:
        category, explanation = categorize_failure(f.get("traceback_summary", ""))
        analyzed.append({
            "test": f.get("test", ""),
            "outcome": f.get("outcome", ""),
            "category": category,
            "explanation": explanation,
            "traceback_summary": f.get("traceback_summary", ""),
        })
    return analyzed


# --------------------------------------------------------------------------- #
# 2. Repair prompt (real Qwen path)                                           #
# --------------------------------------------------------------------------- #
def build_repair_prompt(code, test_code, analyzed_failures):
    """Ask Qwen to repair the code under test given the failing tests."""
    failure_block = "\n".join(
        f"- {a['test']} [{a['category']}]: {a['explanation']}\n"
        f"  traceback: {a['traceback_summary']}"
        for a in analyzed_failures
    )
    return f"""You are Agent C: Debugger in an LLM-based Software Engineering Agent system.

The code below was produced by Agent B. The pytest suite below fails.
Diagnose the root cause and return a corrected version of the CODE UNDER TEST.

Failing tests and analysis:
{failure_block}

Code under test:
```python
{code}
```

Test module (do NOT change the tests; fix the code so the tests pass):
```python
{test_code}
```

Rules:
1. Return ONLY the corrected Python code for the module under test.
2. No markdown fences, no prose, no test code.
3. Keep the same class name and public method names the tests rely on.
4. The file must pass ast.parse.
"""


def qwen_repair_code(code, test_code, analyzed_failures):
    import time
    if not _DASHSCOPE_AVAILABLE:
        raise RuntimeError("dashscope not installed")
    load_dotenv()
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY is missing. Check your .env file.")
    dashscope.api_key = api_key
    dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
    prompt = build_repair_prompt(code, test_code, analyzed_failures)
    t0 = time.time()
    response = dashscope.Generation.call(model="qwen-max", prompt=prompt)
    elapsed = round(time.time() - t0, 3)
    if response.status_code != 200:
        if _log_call:
            try:
                _log_call(provider="qwen", model="qwen-max", prompt=prompt,
                          elapsed=elapsed, agent="agent_c_debugger", success=False,
                          error=f"{response.code} - {response.message}")
            except Exception:
                pass
        raise RuntimeError(f"Qwen call failed: {response.code} - {response.message}")
    if _log_call:
        try:
            usage = getattr(response, "usage", None)
            class _U:
                prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0)
                completion_tokens = int(getattr(usage, "output_tokens", 0) or 0)
                total_tokens = prompt_tokens + completion_tokens
            _log_call(provider="qwen", model="qwen-max", prompt=prompt,
                      elapsed=elapsed, agent="agent_c_debugger", success=True, usage=_U())
        except Exception:
            pass
    content = response.output.get("text") or (
        response.output["choices"][0]["message"]["content"]
    )
    return extract_code_from_text(content)


# --------------------------------------------------------------------------- #
# 3. Deterministic mock fixer (fallback, no network needed)                   #
# --------------------------------------------------------------------------- #
# Targeted, safe source transforms keyed off the failure category. These are
# conservative: they only fire on well-understood patterns produced by the
# Agent-B CRUD-manager shape, and otherwise leave the code unchanged.
def mock_repair_code(code, analyzed_failures):
    """
    Apply small, well-understood source fixes based on the failure categories.
    Returns (fixed_code, applied_fixes:list[str]).
    """
    fixed = code
    applied = []
    categories = {a["category"] for a in analyzed_failures}

    # Fix 1: a method that should return (bool, msg) but returns only a bool,
    # which makes `ok, msg = manager.method(...)` raise TypeError (not iterable
    # / cannot unpack). We normalize bare `return True/False` inside methods to
    # the (bool, message) tuple convention the rest of the class uses.
    if "TypeError" in categories:
        before = fixed
        # Match a `return True` / `return False` that is the WHOLE statement
        # (end of line, optional trailing comment) and is not already a tuple.
        fixed = re.sub(
            r"^(?P<indent>[ \t]+)return True[ \t]*$",
            r'\g<indent>return True, "ok"',
            fixed,
            flags=re.MULTILINE,
        )
        fixed = re.sub(
            r"^(?P<indent>[ \t]+)return False[ \t]*$",
            r'\g<indent>return False, "error"',
            fixed,
            flags=re.MULTILINE,
        )
        if fixed != before:
            applied.append(
                "TypeError: normalized bare boolean returns to the "
                "(bool, message) tuple convention used by the class."
            )

    # Fix 2: missing-existence guard causing KeyError on lookup/delete/update.
    # If a method does `del self.<store>[key]` or `self.<store>[key]` without a
    # membership check, this is reported in analysis; we do not blindly rewrite
    # arbitrary code, so we only annotate. (Conservative: avoids breaking code.)
    if "KeyError" in categories:
        applied.append(
            "KeyError: flagged a dict access without a membership check; "
            "recommend `if key in store:` guard (left for Qwen/human review)."
        )

    # Fix 3: AttributeError from a misspelled method name is not safely
    # auto-fixable without guessing intent; flag for the LLM/human path.
    if "AttributeError" in categories:
        applied.append(
            "AttributeError: method name in implementation likely differs "
            "from the tested API; recommend Qwen repair or rename."
        )

    return fixed, applied


# --------------------------------------------------------------------------- #
# 3b. Test-side repair (the failure is in Agent C's OWN generated test file)  #
# --------------------------------------------------------------------------- #
# Key insight: a collection_error / ImportError / test-level NameError is
# almost never a bug in the code under test -- it is a defect in the *generated
# test file* (a missing stdlib import, a `@patch`/`patch(...)` used without
# importing unittest.mock, or the module-under-test not being importable by the
# name the test uses). Repairing the *code* in those cases is a no-op, which is
# exactly why the debugger used to get stuck at fix_unverified (0/1 -> 0/1).
#
# These transforms repair the TEST, not the code. They are conservative and
# only inject missing imports / a sys.path bootstrap; they never edit assertions
# or test logic. No schema change -- `fixed_code` still carries the corrected
# code, and the applied_fixes list records that the test file was repaired.

# Categories whose root cause lives in the generated test module rather than in
# the code under test.
_TEST_SIDE_CATEGORIES = {"collection_error", "ImportError"}


def _failure_is_test_side(analyzed_failures):
    """
    Decide whether the failure(s) point at the generated test file rather than
    the code under test. True when any failure is a collection/import error, or
    a NameError raised at test *collection* time (decorator evaluated before any
    test runs, e.g. `@patch(...)` with unittest.mock not imported).
    """
    for a in analyzed_failures:
        cat = a.get("category", "")
        tb = a.get("traceback_summary", "") or ""
        if cat in _TEST_SIDE_CATEGORIES:
            return True
        # A NameError surfaced during collection (no test ran yet) is a broken
        # test module, not a code bug. The synthesized collection entry above
        # already covers most of these, but a raw NameError at import time can
        # slip through as category NameError.
        if cat == "NameError" and (
            "during collection" in tb
            or "ERROR collecting" in tb
            or "in <module>" in tb
        ):
            return True
    return False


def repair_test_code(test_code, module_filename):
    """
    Repair the generated TEST module for the common Agent-C-side defects that
    cause a collection error. Returns (fixed_test, applied_fixes:list[str]).

    Conservative, deterministic, no network:
      1. Inject missing stdlib imports the test body uses (reuses the tester's
         patch_missing_imports: time/hashlib/json/re/os/sys/...).
      2. If the test uses `@patch` / `patch(`/ `MagicMock(` / `Mock(` but never
         imports unittest.mock, add `from unittest.mock import patch, MagicMock`.
      3. If the test imports the module-under-test by name, prepend a sys.path
         bootstrap so the import resolves regardless of pytest's rootdir. The
         sandbox writes the module next to the test, so inserting the test's own
         directory on sys.path makes `from <module> import ...` robust.
    """
    applied = []
    fixed = test_code

    # 1. Missing stdlib imports (e.g. test computes a real hash but forgot
    #    `import hashlib`). Reuses the exact tester helper for consistency.
    after_stdlib = patch_missing_imports(fixed)
    if after_stdlib != fixed:
        added = [
            ln for ln in after_stdlib.splitlines()
            if ln.startswith("import ") and ln not in fixed
        ]
        fixed = after_stdlib
        applied.append(
            "test-repair: injected missing stdlib import(s) "
            f"{', '.join(added)} that the generated test used but did not import."
        )

    # 2. unittest.mock used but not imported -> classic collection NameError on
    #    `@patch(...)` (the decorator is evaluated at import time).
    uses_mock = re.search(r"@?\bpatch\s*\(|\bMagicMock\s*\(|\bMock\s*\(", fixed)
    imports_mock = re.search(
        r"^\s*(from\s+unittest(\.mock)?\s+import|import\s+unittest\.mock|"
        r"from\s+mock\s+import|import\s+mock)\b",
        fixed, flags=re.MULTILINE,
    )
    if uses_mock and not imports_mock:
        fixed = "from unittest.mock import patch, MagicMock, Mock\n" + fixed
        applied.append(
            "test-repair: added `from unittest.mock import patch, MagicMock, "
            "Mock` (the test used patch/Mock at collection time without "
            "importing it -> NameError during collection)."
        )

    # 3. Module-under-test import bootstrap. The sandbox writes the module
    #    beside the test, so put the test file's own dir on sys.path. Idempotent.
    module = module_filename[:-3] if module_filename.endswith(".py") else module_filename
    imports_module = re.search(
        rf"^\s*(from\s+{re.escape(module)}\s+import|import\s+{re.escape(module)})\b",
        fixed, flags=re.MULTILINE,
    )
    already_bootstrapped = "sys.path.insert(0, os.path.dirname(__file__)" in fixed
    if imports_module and not already_bootstrapped:
        bootstrap = (
            "import os, sys\n"
            "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
        )
        fixed = bootstrap + fixed
        applied.append(
            f"test-repair: prepended a sys.path bootstrap so `import {module}` "
            "resolves to the sandbox copy regardless of pytest rootdir."
        )

    return fixed, applied


# --------------------------------------------------------------------------- #
# 4. Main debug workflow: analyze -> fix -> verify (fix-verify loop)          #
# --------------------------------------------------------------------------- #
def run_agent_c_debugger(test_output_path, output_dir, max_attempts=1):
    """
    Read a test_output.json (from the Week 2 tester), and if it contains
    failures, analyze them, attempt a fix, and re-run to verify.
    """
    with open(test_output_path, "r", encoding="utf-8") as f:
        test_output = json.load(f)

    code_filename = test_output["tested_file"]
    test_code = test_output["test_code"]
    execution = test_output.get("execution", {})
    failures = execution.get("failures", [])

    # The code under test must be available. Week 2 wrote it into the sandbox
    # tempdir; here we re-read it from the Agent B output next to the report.
    impl_path = os.path.join(output_dir, "implementation_output.json")
    with open(impl_path, "r", encoding="utf-8") as f:
        code = json.load(f)["code"]

    # No failures -> nothing to debug.
    if not failures:
        result = {
            "status": "no_failures",
            "message": "Tester reported no failing tests; debugger is a no-op.",
            "tested_file": code_filename,
            "analysis": [],
            "fix_attempted": False,
            "verified": True,
        }
        _write(output_dir, result)
        return result

    # Step 1: analyze.
    analysis = analyze_failures(failures)

    # Step 1b: decide which side the failure is on. A collection_error /
    # ImportError / collection-time NameError is a defect in Agent C's OWN
    # generated test file, not in the code under test. Repairing the code in
    # that case is a no-op (the same broken test fails to collect again), which
    # is exactly the fix_unverified 0/1 -> 0/1 stall. So we repair the TEST.
    test_side = _failure_is_test_side(analysis)

    # Defaults; overwritten by whichever branch runs.
    mode = "qwen_repair"
    retry_used = False
    retry_reason = "none"
    fix_target = "code_under_test"
    fixed_code = code
    fixed_test_code = test_code

    if test_side:
        # --- Repair the generated test file deterministically (no network). ---
        fix_target = "test_file"
        mode = "test_repair"
        fixed_test_code, applied_fixes = repair_test_code(test_code, code_filename)
        if not applied_fixes:
            # Nothing matched our safe transforms; fall back to the code-repair
            # path so we still attempt *something* rather than silently stalling.
            fix_target = "code_under_test"
            mode = "qwen_repair"
            try:
                fixed_code = qwen_repair_code(code, test_code, analysis)
                applied_fixes = ["qwen_repair: model returned a corrected module."]
            except Exception as error:  # noqa: BLE001
                fixed_code, applied_fixes = mock_repair_code(code, analysis)
                mode = "mock_fixer_fallback"
                retry_used = True
                retry_reason = f"qwen_unavailable_fallback_to_mock: {error}"
    else:
        # --- Repair the code under test (original behavior). ---
        try:
            fixed_code = qwen_repair_code(code, test_code, analysis)
            applied_fixes = ["qwen_repair: model returned a corrected module."]
        except Exception as error:  # noqa: BLE001
            fixed_code, applied_fixes = mock_repair_code(code, analysis)
            mode = "mock_fixer_fallback"
            retry_used = True
            retry_reason = f"qwen_unavailable_fallback_to_mock: {error}"

    # Validate the artifact we changed parses before we re-run.
    artifact_to_check = fixed_test_code if fix_target == "test_file" else fixed_code
    try:
        ast.parse(artifact_to_check)
        fix_syntax = "passed"
    except SyntaxError as error:
        fix_syntax = f"failed: {error}"

    # Step 3: verify -- re-run in the sandbox. When we repaired the test, run
    # the (unchanged) code against the FIXED test; otherwise the fixed code
    # against the original test.
    verify = run_tests_in_sandbox(fixed_code, fixed_test_code, code_filename)
    verified = (
        verify.get("executed", False)
        and verify.get("total", 0) > 0
        and verify.get("failed", 1) == 0
    )

    result = {
        "status": "fix_verified" if verified else "fix_unverified",
        "tested_file": code_filename,
        "mode": mode,
        "fix_target": fix_target,
        "retry_used": retry_used,
        "retry_reason": retry_reason,
        "fix_syntax_check": fix_syntax,
        "fix_attempted": True,
        "applied_fixes": applied_fixes,
        "analysis": analysis,
        "before": {
            "passed": execution.get("passed", 0),
            "failed": execution.get("failed", 0),
            "total": execution.get("total", 0),
        },
        "after": {
            "passed": verify.get("passed", 0),
            "failed": verify.get("failed", 0),
            "total": verify.get("total", 0),
        },
        "verified": verified,
        "fixed_code": fixed_code,
        "fixed_test_code": fixed_test_code,
    }
    _write(output_dir, result)
    return result


def _write(output_dir, result):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "debug_output.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    test_out = sys.argv[1] if len(sys.argv) > 1 else "outputs/test_output.json"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "outputs"
    res = run_agent_c_debugger(test_out, out_dir)
    printable = {k: v for k, v in res.items() if k != "fixed_code"}
    print(json.dumps(printable, indent=4, ensure_ascii=False))
