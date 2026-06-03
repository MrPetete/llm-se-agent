"""
Docker sandbox runner (reference isolation environment).

Talks to Docker via the **Docker CLI through subprocess**, NOT the Python docker
SDK. This is an intentional implementation choice:
  * The M5 guide suggested the Python ``docker`` SDK.
  * The actual environment has the Docker CLI installed but NOT the SDK.
  * Using the CLI avoids adding a new dependency and matches the project's
    existing subprocess style (M4's runner).
All commands are list-style argv (never ``shell=True``).

Isolation flags applied to ``docker run``:
  --rm --network none --memory 256m --cpus 1 --pids-limit 128
  --user 65534:65534   (run as nobody, never root)

Only the two generated files (module + test) are placed in a private host
tempdir that is bind-mounted to /sandbox. The repo, .env, logs, and source tree
are never mounted. ``--network none`` means sandboxed code has no internet.
"""

import json
import os
import subprocess
import tempfile
import uuid


def docker_available(timeout=5):
    """
    Return (ok: bool, reason: str|None). ok=True means the Docker daemon is
    reachable. reason explains why not, for use as a fallback_reason.
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0:
            return True, None
        return False, (result.stderr.strip() or result.stdout.strip()
                       or "Docker daemon unavailable")
    except FileNotFoundError:
        return False, "Docker CLI not found"
    except subprocess.TimeoutExpired:
        return False, "Docker availability check timed out"


def image_exists(image, timeout=10):
    """Return True if the sandbox image is present locally (no network pull)."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# Inside the container: copy the read-only inputs into a writable tmpfs workdir,
# run pytest (its output -> stderr), then emit ONLY report.json on stdout.
_CONTAINER_SCRIPT = (
    "cp /input/*.py /sandbox/ && "
    "(python -m pytest test_generated.py -q --json-report "
    "--json-report-file=/sandbox/report.json 1>&2); "
    "cat /sandbox/report.json 2>/dev/null"
)


def _docker_failure(message, return_code=None):
    """Clear Docker-mode failure (Docker WAS available; run failed). No fallback."""
    return {
        "executed": False,
        "timed_out": False,
        "passed": 0, "failed": 0, "total": 0,
        "failures": [],
        "return_code": return_code,
        "stdout": "",
        "stderr": message[-2000:],
        "sandbox_mode": "docker",
        "fallback_reason": None,
    }


def run_in_docker(code, test_code, module_filename, image, timeout=30):
    """
    Run the generated suite inside a throwaway, network-isolated container.

    Returns the standard result dict with sandbox_mode="docker". Callers must
    only invoke this AFTER docker_available() and image_exists() are confirmed,
    so any failure here is a real Docker-mode failure (NOT an availability
    problem) and is surfaced rather than silently falling back.
    """
    host_input = tempfile.mkdtemp(prefix="agent_c_docker_")
    with open(os.path.join(host_input, module_filename), "w", encoding="utf-8") as f:
        f.write(code)
    with open(os.path.join(host_input, "test_generated.py"), "w", encoding="utf-8") as f:
        f.write(test_code)

    name = f"agent_c_sandbox_{uuid.uuid4().hex[:12]}"
    cmd = [
        "docker", "run", "--rm", "--name", name,
        "--network", "none", "--memory", "256m", "--cpus", "1",
        "--pids-limit", "128", "--user", "65534:65534",
        "-v", f"{host_input}:/input:ro",
        "--tmpfs", "/sandbox:rw,size=64m,uid=65534,gid=65534", "--workdir", "/sandbox",
        image, "sh", "-c", _CONTAINER_SCRIPT,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        # Killing the CLI may not remove the container -> force remove by name.
        subprocess.run(["docker", "rm", "-f", name],
                       capture_output=True, text=True)
        return {
            "executed": True,
            "timed_out": True,
            "passed": 0, "failed": 0, "total": 0,
            "failures": [],
            "return_code": None,
            "stdout": "",
            "stderr": (f"Docker sandbox timed out after {timeout}s.\n"
                       + ((exc.stderr or "")[-1500:] if exc.stderr else "")),
            "sandbox_mode": "docker",
            "fallback_reason": None,
        }

    # report.json is printed on stdout by the container script. If we can parse
    # it, this is a normal pytest result (nonzero exit just means tests failed).
    # If it is absent, Docker failed before tests produced a report.
    report = None
    if proc.stdout.strip():
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError:
            report = None

    if report is None:
        return _docker_failure(
            "Docker ran but produced no parseable test report. "
            f"docker stderr:\n{proc.stderr[-1500:]}",
            return_code=proc.returncode,
        )

    s = report.get("summary", {})
    failures = []
    for t in report.get("tests", []):
        if t.get("outcome") != "passed":
            call = t.get("call", {})
            failures.append({
                "test": t.get("nodeid", ""),
                "outcome": t.get("outcome", ""),
                "traceback_summary": (call.get("longrepr", "") or "")[-600:],
            })

    return {
        "executed": True,
        "timed_out": False,
        "passed": s.get("passed", 0),
        "failed": s.get("failed", 0),
        "total": s.get("total", 0),
        "failures": failures,
        "return_code": proc.returncode,
        "stdout": proc.stderr[-2000:],  # pytest output was redirected to stderr
        "stderr": proc.stderr[-2000:],
        "sandbox_mode": "docker",
        "fallback_reason": None,
    }
