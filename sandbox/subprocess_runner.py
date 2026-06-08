"""
Subprocess sandbox runner

RELOCATED body of M4's original ``run_tests_in_sandbox`` from
``agents/agent_c/agent_c_tester.py``. Logic preserved (temp dir, pytest
invocation, structured pass/fail parsing, timeout handling).

This is the compatibility / fallback execution path. Docker is the reference
isolation environment (see ``docker_runner.py``); this subprocess path is NOT
full security isolation -- it runs on the host Python interpreter.

Owner note: M4 owns Agent C. M5 relocated this function so that
``sandbox_runner.py`` can route between Docker and this fallback. M5 hardening
(this revision): the runner no longer hard-depends on the
``pytest-json-report`` plugin being installed in ``sys.executable``. It probes
for the plugin once; if present it uses ``--json-report`` (rich data), and if
absent it falls back to ``--junitxml`` (built into pytest core, no plugin) and
parses the JUnit XML with the stdlib. The previous behavior -- where a missing
plugin produced a misleading "ERROR collecting test_generated.py /
unrecognized arguments: --json-report" -- is gone. The returned dict shape is
unchanged; ``report_format`` is additive.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def _json_report_available():
    """True if pytest-json-report is importable in the runner interpreter."""
    try:
        import pytest_jsonreport  # noqa: F401
        return True
    except Exception:  # pragma: no cover - environment dependent
        return False


def _parse_json_report(report_path):
    """Parse a pytest-json-report file -> (summary, failures)."""
    summary = {"passed": 0, "failed": 0, "total": 0}
    failures = []
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
                "traceback_summary": (call.get("longrepr", "") or "")[-600:],
            })
    return summary, failures


def _parse_junit_xml(report_path):
    """
    Parse a pytest --junitxml file -> (summary, failures), matching the shape
    produced by _parse_json_report. Uses only the stdlib.

    JUnit semantics: total = tests attribute; failed = failures + errors;
    passed = total - failed - skipped. A <testcase> with a <failure>, <error>,
    or <skipped> child did not pass.
    """
    summary = {"passed": 0, "failed": 0, "total": 0}
    failures = []
    tree = ET.parse(report_path)
    root = tree.getroot()
    # pytest may emit <testsuites><testsuite>...</testsuite></testsuites> or a
    # bare <testsuite>. Collect all testsuite elements either way.
    suites = root.findall("testsuite")
    if root.tag == "testsuite":
        suites = [root]

    total = errors = fails = skipped = 0
    for suite in suites:
        total += int(suite.get("tests", 0))
        errors += int(suite.get("errors", 0))
        fails += int(suite.get("failures", 0))
        skipped += int(suite.get("skipped", 0))
        for case in suite.findall("testcase"):
            classname = case.get("classname", "")
            name = case.get("name", "")
            nodeid = f"{classname}::{name}" if classname else name
            bad = case.find("failure")
            outcome = None
            if bad is not None:
                outcome = "failed"
            else:
                bad = case.find("error")
                if bad is not None:
                    outcome = "error"
            if outcome is not None:
                detail = (bad.get("message", "") + "\n" + (bad.text or "")).strip()
                failures.append({
                    "test": nodeid,
                    "outcome": outcome,
                    "traceback_summary": detail[-600:],
                })

    summary["total"] = total
    summary["failed"] = fails + errors
    summary["passed"] = max(total - fails - errors - skipped, 0)
    return summary, failures


def run_tests_in_subprocess(code, test_code, module_filename, timeout=30):
    """
    Execute the generated pytest suite in an isolated subprocess with a timeout.
    Returns structured pass/fail data. Uses pytest-json-report when available,
    otherwise falls back to pytest's built-in --junitxml (no plugin required).
    """
    workdir = tempfile.mkdtemp(prefix="agent_c_sandbox_")
    code_path = os.path.join(workdir, module_filename)
    test_path = os.path.join(workdir, "test_generated.py")

    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(test_code)

    use_json = _json_report_available()
    if use_json:
        report_path = os.path.join(workdir, "report.json")
        report_format = "json_report"
        cmd = [
            sys.executable, "-m", "pytest", test_path,
            "-q", "-p", "no:cacheprovider",
            "--json-report", f"--json-report-file={report_path}",
        ]
    else:
        report_path = os.path.join(workdir, "report.xml")
        report_format = "junit_xml"
        cmd = [
            sys.executable, "-m", "pytest", test_path,
            "-q", "-p", "no:cacheprovider",
            f"--junitxml={report_path}",
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
            "return_code": None,
            "stdout": (exc.stdout or "")[-2000:] if exc.stdout else "",
            "stderr": (exc.stderr or "")[-2000:] if exc.stderr else "",
            "report_format": report_format,
        }

    summary = {"passed": 0, "failed": 0, "total": 0}
    failures = []
    if os.path.exists(report_path):
        try:
            if report_format == "json_report":
                summary, failures = _parse_json_report(report_path)
            else:
                summary, failures = _parse_junit_xml(report_path)
        except Exception as parse_err:  # noqa: BLE001
            failures = [{
                "test": "test_generated.py",
                "outcome": "error",
                "traceback_summary": f"Failed to parse {report_format} report: {parse_err}",
            }]
            summary = {"passed": 0, "failed": 1, "total": 1}

    # If pytest exited non-zero but wrote no parseable report (collection error
    # / import error), synthesize a failure entry so the debugger can see it.
    if proc.returncode != 0 and summary["total"] == 0:
        stderr_out = (proc.stderr or proc.stdout or "")[-1500:]
        failures = [{
            "test": "test_generated.py",
            "outcome": "error",
            "traceback_summary": f"ERROR collecting test_generated.py\n{stderr_out}",
        }]
        summary["failed"] = 1
        summary["total"] = 1

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
        "report_format": report_format,
    }
