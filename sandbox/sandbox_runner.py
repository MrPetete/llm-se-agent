"""
Public sandbox entry point: ``run_tests_in_sandbox`` (Docker-first, fallback).

Routing:
  1. Sanitize module_filename (basename, .py, no traversal).
  2. If sandbox_require_docker and Docker unavailable/image-missing
     -> return docker_required_failed (no fallback).
  3. If Docker available + image present -> run in Docker. A Docker-mode bug
     (bad command, parse error, permission) is surfaced, NOT silently masked.
  4. If Docker CLI missing / daemon down / image missing (default mode)
     -> fall back to the subprocess runner, recording fallback_reason.

Existing return keys are preserved exactly; sandbox_mode / fallback_reason /
stderr are additive.

M4 owns Agent C; M5 only hardens the execution sandbox. Agent C behavior is
preserved except for execution-mode routing (this module), made transparent via
the sandbox_mode / fallback_reason keys.
"""

from config import settings
from sandbox import docker_runner, subprocess_runner


def _sanitize_module_filename(module_filename):
    """Return (ok, reason). Must be a simple .py basename, no path traversal."""
    if not isinstance(module_filename, str) or not module_filename:
        return False, "module_filename must be a non-empty string"
    if not module_filename.endswith(".py"):
        return False, "module_filename must end with .py"
    if "/" in module_filename or "\\" in module_filename:
        return False, "module_filename must not contain path separators"
    if ".." in module_filename:
        return False, "module_filename must not contain '..'"
    if module_filename != module_filename.strip() or module_filename.startswith("."):
        return False, "module_filename must be a plain filename"
    return True, None


def _strict_failure(reason):
    """sandbox_require_docker=True but Docker unavailable. Integer counts."""
    return {
        "executed": False,
        "timed_out": False,
        "passed": 0, "failed": 0, "total": 0,
        "failures": [],
        "return_code": None,
        "stdout": "",
        "stderr": "Docker sandbox required but Docker is unavailable.",
        "sandbox_mode": "docker_required_failed",
        "fallback_reason": reason,
    }


def _bad_input(reason):
    """module_filename failed sanitization. Surface clearly, run nothing."""
    return {
        "executed": False,
        "timed_out": False,
        "passed": 0, "failed": 0, "total": 0,
        "failures": [],
        "return_code": None,
        "stdout": "",
        "stderr": f"Invalid module_filename: {reason}",
        "sandbox_mode": "invalid_input",
        "fallback_reason": reason,
    }


def run_tests_in_sandbox(code, test_code, module_filename, timeout=None):
    """
    Public sandbox entry point. Drop-in replacement for M4's original function:
    same signature and same existing return keys, plus additive sandbox_mode /
    fallback_reason / stderr.

    Docker-first with visible subprocess fallback (default), or strict Docker
    when settings.sandbox_require_docker is True.
    """
    if timeout is None:
        timeout = settings.sandbox_timeout_seconds

    ok, reason = _sanitize_module_filename(module_filename)
    if not ok:
        return _bad_input(reason)

    image = settings.sandbox_image
    require_docker = settings.sandbox_require_docker

    available, why = docker_runner.docker_available()
    has_image = available and docker_runner.image_exists(image)

    if available and has_image:
        # Docker is usable. Any failure inside here is a real Docker-mode bug
        # and is surfaced (not masked by fallback).
        return docker_runner.run_in_docker(
            code, test_code, module_filename, image, timeout
        )

    # Docker not usable: availability / setup problem.
    if not available:
        unavailable_reason = why or "Docker daemon unavailable"
    else:
        unavailable_reason = (
            f"Docker image not found. Build it with: "
            f"docker build -f Dockerfile.sandbox -t {image} ."
        )

    if require_docker:
        return _strict_failure(unavailable_reason)

    # Default mode: fall back to subprocess, recording why.
    result = subprocess_runner.run_tests_in_subprocess(
        code, test_code, module_filename, timeout
    )
    result["sandbox_mode"] = "subprocess_fallback"
    result["fallback_reason"] = unavailable_reason
    return result
