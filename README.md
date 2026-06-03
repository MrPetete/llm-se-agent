# llm-se-agent
LLM-Based Software Engineering Agent — CrewAI multi-agent system

## Agent C Sandbox (test execution)

Agent C runs AI-generated code and its tests inside a sandbox. There are two
execution modes, chosen automatically:

- **`docker`** — the reference isolation environment. Code runs in a throwaway,
  network-disabled container (`--network none`, memory/CPU/PID limits, runs as
  the unprivileged `nobody` user). Only the generated module + test file are
  passed in; the repo, `.env`, and logs are never mounted.
- **`subprocess_fallback`** — a compatibility mode used when Docker is
  unavailable (Docker Desktop not running, or CI with no daemon). It runs tests
  in a host subprocess. This is **NOT full security isolation** — it is a
  best-effort fallback so the pipeline keeps working everywhere.

Every result includes a `sandbox_mode` field (and `fallback_reason` when it
fell back), so the active mode is always visible.

### Setup (VS Code PowerShell, Anaconda Python 3.11.7)

```powershell
# from the repo root (confirm with Get-Location)
conda activate <your-env>          # Python 3.11.7
pip install -r requirements.txt    # includes pytest-json-report (required by the runner)

# Start Docker Desktop, then build the sandbox image:
docker build -f Dockerfile.sandbox -t llm-se-agent-sandbox:latest .

# Verify sandbox readiness (Docker checks are advisory unless require_docker):
python scripts/doctor.py

# Run the sandbox tests:
python -m pytest tests/test_sandbox.py -q
```

### Configuration (`config.py` / `.env`)

- `sandbox_timeout_seconds` (default 30) — per-run timeout.
- `sandbox_image` (default `llm-se-agent-sandbox:latest`) — the image to run.
- `sandbox_require_docker` (default `False`) — when `True`, the sandbox refuses
  to fall back and returns `sandbox_mode="docker_required_failed"` if Docker is
  unavailable. Use in environments that require guaranteed isolation.

### Notes

- Docker mode uses `--network none`: **sandboxed generated code must not depend
  on internet access.**
- If the image is missing, the runner does not pull from the internet; it tells
  you to build it with the command above.
