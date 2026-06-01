import sys
import os
import importlib.metadata
from pathlib import Path

checks = []

def check(name, cond, hint=""):
    checks.append((name, cond, hint))

check("Python >= 3.10", sys.version_info >= (3, 10), "Install Python 3.10+")

try:
    openai_ver = importlib.metadata.version("openai")
    openai_ok = openai_ver.startswith(("2.", "3."))
except importlib.metadata.PackageNotFoundError:
    openai_ok = False
check("openai >= 2.0", openai_ok, "pip install -U openai")

check(".env present", Path(".env").exists(), "Copy .env.example to .env")
check("DASHSCOPE_API_KEY set", bool(os.getenv("DASHSCOPE_API_KEY")), "Add DASHSCOPE_API_KEY to .env")

logs = Path("logs")
check("logs/ writable", os.access(logs if logs.exists() else Path("."), os.W_OK), "Check folder permissions")

ok = True
for name, cond, hint in checks:
    print(f"{'OK' if cond else 'FAIL'} {name}")
    if not cond:
        print(f"   -> {hint}")
        ok = False

sys.exit(0 if ok else 1)
