import sys
import os
import subprocess
import importlib.metadata
from pathlib import Path

checks = []
warnings = []


def check(name, cond, hint=""):
    checks.append((name, cond, hint))


def warn(name, cond, hint=""):
    """Advisory check: reported but does not fail doctor (unless promoted)."""
    warnings.append((name, cond, hint))


check("Python >= 3.10", sys.version_info >= (3, 10), "Install Python 3.10+")

try:
    openai_ver = importlib.metadata.version("openai")
    openai_ok = openai_ver.startswith(("2.", "3."))
except importlib.metadata.PackageNotFoundError:
    openai_ok = False
check("openai >= 2.0", openai_ok, "pip install -U openai")

check(".env present", Path(".env").exists(), "Copy .env.example to .env")
check(
    "DASHSCOPE_API_KEY set",
    bool(os.getenv("DASHSCOPE_API_KEY")),
    "Add DASHSCOPE_API_KEY to .env",
)

logs = Path("logs")
check(
    "logs/ writable",
    os.access(logs if logs.exists() else Path("."), os.W_OK),
    "Check folder permissions",
)


# --- Docker sandbox readiness (Week 4). Advisory unless require_docker. ------ #
def _docker_ok(args, timeout=5):
    try:
        return subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=timeout
        ).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import settings
    sandbox_image = settings.sandbox_image
    require_docker = settings.sandbox_require_docker
except Exception:
    sandbox_image, require_docker = "llm-se-agent-sandbox:latest", False

docker_cli = _docker_ok(["--version"])
docker_daemon = docker_cli and _docker_ok(["info"])
docker_image = docker_daemon and _docker_ok(["image", "inspect", sandbox_image])

sandbox_record = check if require_docker else warn
sandbox_record("Docker CLI installed", docker_cli,
               "Install Docker Desktop (sandbox falls back to subprocess if absent)")
sandbox_record("Docker daemon running", docker_daemon,
               "Start Docker Desktop to enable isolated sandbox mode")
sandbox_record(
    f"Sandbox image '{sandbox_image}' built", docker_image,
    f"docker build -f Dockerfile.sandbox -t {sandbox_image} .",
)

ok = True
for name, cond, hint in checks:
    print(f"{'OK' if cond else 'FAIL'} {name}")
    if not cond:
        print(f"   -> {hint}")
        ok = False

for name, cond, hint in warnings:
    print(f"{'OK' if cond else 'WARN'} {name}")
    if not cond:
        print(f"   -> {hint}")

sys.exit(0 if ok else 1)
