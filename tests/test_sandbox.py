"""
Tests for the M5 Week 4 sandbox package (sandbox/).

These cover the ROUTING logic and the relocated subprocess runner. Real Docker
execution is mocked so the suite passes in CI (no Docker daemon there). The one
test that needs a live daemon is guarded with a skip.

Run (PowerShell, from repo root, Anaconda 3.11):
    python -m pytest tests/test_sandbox.py -q
"""

import importlib
import subprocess

import pytest

from sandbox import docker_runner, sandbox_runner
from sandbox.subprocess_runner import run_tests_in_subprocess


class _Done:
    """Minimal stand-in for a completed subprocess.run result."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


# A tiny self-contained module + test the sandbox can actually run.
GOOD_CODE = "def add(a, b):\n    return a + b\n"
GOOD_TEST = (
    "from sample import add\n\n\n"
    "def test_add():\n"
    "    assert add(2, 3) == 5\n"
)
FAILING_TEST = (
    "from sample import add\n\n\n"
    "def test_add_wrong():\n"
    "    assert add(2, 3) == 6\n"
)
SYNTAX_ERROR_TEST = "def test_broken(:\n    pass\n"
INFINITE_TEST = (
    "def test_loops():\n"
    "    while True:\n"
    "        pass\n"
)


def test_no_circular_import():
    """Importing the runner + both agent_c modules in one process must not loop."""
    importlib.import_module("sandbox.sandbox_runner")
    importlib.import_module("agents.agent_c.agent_c_tester")
    importlib.import_module("agents.agent_c.agent_c_debugger")


def test_subprocess_passing():
    """Relocated subprocess runner: passing suite -> executed, no failures."""
    r = run_tests_in_subprocess(GOOD_CODE, GOOD_TEST, "sample.py", timeout=60)
    assert r["executed"] is True
    assert r["failed"] == 0
    assert r["passed"] >= 1
    assert isinstance(r["passed"], int) and isinstance(r["failed"], int)


def test_subprocess_failing():
    """Failing assertion -> failed count > 0, still executed."""
    r = run_tests_in_subprocess(GOOD_CODE, FAILING_TEST, "sample.py", timeout=60)
    assert r["executed"] is True
    assert r["failed"] >= 1


def test_subprocess_syntax_error_useful_output():
    """A broken test file still returns a structured result with output."""
    r = run_tests_in_subprocess(GOOD_CODE, SYNTAX_ERROR_TEST, "sample.py", timeout=60)
    assert "stderr" in r and "stdout" in r
    assert r["failed"] >= 0  # no crash; structured dict returned


def test_subprocess_timeout():
    """Infinite loop trips the timeout branch."""
    r = run_tests_in_subprocess(GOOD_CODE, INFINITE_TEST, "sample.py", timeout=3)
    assert r["timed_out"] is True
    assert r["executed"] is False


def test_invalid_module_filename_rejected():
    """Path-traversal / non-.py names are refused before anything runs."""
    for bad in ["../evil.py", "a/b.py", "evil.txt", "..", "/abs.py"]:
        r = sandbox_runner.run_tests_in_sandbox(GOOD_CODE, GOOD_TEST, bad)
        assert r["sandbox_mode"] == "invalid_input"
        assert r["executed"] is False


def test_fallback_when_docker_unavailable(monkeypatch):
    """Docker down + default mode -> subprocess_fallback with a reason."""
    monkeypatch.setattr(docker_runner, "docker_available",
                        lambda timeout=5: (False, "Docker daemon unavailable"))
    monkeypatch.setattr(sandbox_runner.settings, "sandbox_require_docker", False)
    r = sandbox_runner.run_tests_in_sandbox(GOOD_CODE, GOOD_TEST, "sample.py", timeout=60)
    assert r["sandbox_mode"] == "subprocess_fallback"
    assert r["fallback_reason"]
    assert r["passed"] >= 1  # subprocess actually ran the test


def test_strict_mode_fails_clearly(monkeypatch):
    """Docker down + strict mode -> docker_required_failed, no fallback."""
    monkeypatch.setattr(docker_runner, "docker_available",
                        lambda timeout=5: (False, "Docker CLI not found"))
    monkeypatch.setattr(sandbox_runner.settings, "sandbox_require_docker", True)
    r = sandbox_runner.run_tests_in_sandbox(GOOD_CODE, GOOD_TEST, "sample.py")
    assert r["sandbox_mode"] == "docker_required_failed"
    assert r["executed"] is False
    assert r["passed"] == 0 and isinstance(r["passed"], int)
    assert "CLI not found" in r["fallback_reason"]


def test_image_missing_gives_build_hint(monkeypatch):
    """Daemon up but image absent (default mode) -> fallback names the build cmd."""
    monkeypatch.setattr(docker_runner, "docker_available", lambda timeout=5: (True, None))
    monkeypatch.setattr(docker_runner, "image_exists", lambda image, timeout=10: False)
    monkeypatch.setattr(sandbox_runner.settings, "sandbox_require_docker", False)
    r = sandbox_runner.run_tests_in_sandbox(GOOD_CODE, GOOD_TEST, "sample.py", timeout=60)
    assert r["sandbox_mode"] == "subprocess_fallback"
    assert "docker build -f Dockerfile.sandbox" in r["fallback_reason"]


def test_sandbox_mode_always_present(monkeypatch):
    """Every routed return path includes sandbox_mode."""
    monkeypatch.setattr(docker_runner, "docker_available",
                        lambda timeout=5: (False, "down"))
    r = sandbox_runner.run_tests_in_sandbox(GOOD_CODE, GOOD_TEST, "sample.py", timeout=60)
    assert "sandbox_mode" in r and "fallback_reason" in r


def test_docker_command_is_list_and_no_shell(monkeypatch):
    """The docker command must be argv-list with shell=False (no injection)."""
    captured = {}

    class _Proc:
        stdout = '{"summary": {"passed": 1, "failed": 0, "total": 1}, "tests": []}'
        stderr = ""
        returncode = 0

    def fake_run(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return _Proc()

    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)
    docker_runner.run_in_docker(GOOD_CODE, GOOD_TEST, "sample.py",
                                "llm-se-agent-sandbox:latest", timeout=30)

    assert isinstance(captured["cmd"], list)          # argv list, not a string
    assert captured["cmd"][0] == "docker"
    assert "shell" not in captured["kwargs"]           # never shell=True
    # Isolation flags present
    for flag in ["--network", "none", "--user", "65534:65534", "--rm"]:
        assert flag in captured["cmd"]


def test_docker_timeout_calls_rm_f(monkeypatch):
    """On timeout, the container is force-removed by name."""
    rm_calls = []

    def fake_run(cmd, *args, **kwargs):
        if cmd[:3] == ["docker", "rm", "-f"]:
            rm_calls.append(cmd)
            return _Done(returncode=0)
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 30))

    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)
    r = docker_runner.run_in_docker(GOOD_CODE, GOOD_TEST, "sample.py",
                                    "llm-se-agent-sandbox:latest", timeout=2)
    assert r["timed_out"] is True
    assert r["sandbox_mode"] == "docker"
    assert rm_calls, "docker rm -f was not called on timeout"


@pytest.mark.skipif(
    docker_runner.docker_available()[0] is False,
    reason="Docker daemon not available",
)
def test_live_docker_round_trip():
    """Live Docker run when a daemon is present and the image is built."""
    if not docker_runner.image_exists("llm-se-agent-sandbox:latest"):
        pytest.skip("sandbox image not built")
    r = docker_runner.run_in_docker(GOOD_CODE, GOOD_TEST, "sample.py",
                                    "llm-se-agent-sandbox:latest", timeout=60)
    assert r["sandbox_mode"] == "docker"
    assert r["passed"] >= 1
