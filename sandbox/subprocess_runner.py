"""
Subprocess sandbox runner.

RELOCATED body of M4's original ``run_tests_in_sandbox`` from
``agents/agent_c/agent_c_tester.py``. Logic preserved exactly (temp dir, pytest
--json-report invocation, JSON parsing, timeout handling). Only additive change:
a ``stderr`` key in the returned dict.

This is the compatibility / fallback execution path. Docker is the reference
isolation environment (see ``docker_runner.py``); this subprocess path is NOT
full security isolation -- it runs on the host Python interpreter.

Owner note: M4 owns Agent C. M5 relocated this function unchanged so that
``sandbox_runner.py`` can route between Docker and this fallback.
"""

import json
import os
import subprocess
import sys
import tempfile


def run_tests_in_subprocess(code, test_code, module_filename, timeout=30):
    """
    Execute the generated pytest suite in an isolated subprocess with a timeout.
    Returns structured pass/fail data parsed from pytest-json-report.

    Behavior preserved from M4's original run_tests_in_sandbox; ``stderr`` added.
    """
    workdir = tempfile.mkdtemp(prefix="agent_c_sandbox_")
    code_path = os.path.join(workdir, module_filename)
    test_path = os.path.join(workdir, "test_generated.py")
    report_path = os.path.join(workdir, "report.json")

    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(test_code)

    cmd = [
        sys.executable, "-m", "pytest", test_path,
        "-q", "--json-report", f"--json-report-file={report_path}",
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        return {
            "executed": False,
            "timed_out": True,
            "passed": 0, "failed": 0, "total": 0,
            "failures": [],
            "stdout": (exc.stdout or "")[-2000:] if exc.stdout else "",
            "stderr": (exc.stderr or "")[-2000:] if exc.stderr else "",
        }
    summary = {"passed": 0, "failed": 0, "total": 0}
    failures = []
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        s = report.get("summary", {})
        summary["passed"] = s.get("passed", 0)
        summary["failed"] = s.get("failed", 0)
        summary["total"] = s.get("total", 0)
        for t in report.get("tests", []):
            if t.get("outcome") != "passed":
                call = t.get("call", {})
                failures.append({
                    "test": t.get("nodeid", ""),
                    "outcome": t.get("outcome", ""),
                    "traceback_summary": (
                        call.get("longrepr", "") or ""
                    )[-600:],
                })

    return {
        "executed": True,
        "timed_out": timed_out,
        "passed": summary["passed"],
        "failed": summary["failed"],
        "total": summary["total"],
        "failures": failures,
        "return_code": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }
