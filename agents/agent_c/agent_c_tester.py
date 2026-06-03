"""
Agent C: Tester & Debugger  --  Week 2 deliverable (test generation).

Pipeline position:
    Agent A (analysis_output.json)
        -> Agent B (implementation_output.json)   <-- INPUT to Agent C
            -> Agent C (test_output.json)          <-- OUTPUT of Agent C

Week 2 scope (per roadmap):
    "Build test generation -- input: code files -> output: pytest test suite."

This module:
  1. Reads Agent B's implementation_output.json (the team contract).
  2. Builds a Qwen prompt asking for a pytest module (parametrized happy-path,
     edge-case, and invalid-input tests).
  3. Calls Qwen via DashScope, with a deterministic mock generator as fallback
     (mirrors Agent B's mock-fallback design so the pipeline never crashes
     when no API key / network is available).
  4. Validates the generated test file with ast.parse.
  5. Runs the suite in a subprocess sandbox (timeout) with --json-report and
     returns structured pass/fail data following test_output.json.

The mock test generator inspects the Agent B class with the `ast` module and
emits real, runnable pytest cases for whatever CRUD manager class Agent B
produced (ProductManager, StudentManager, ...). It is not hard-coded to one
class -- it discovers the methods.
"""

import ast
import json
import os
import re
import sys

try:
    from dotenv import load_dotenv
    import dashscope
    _DASHSCOPE_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _DASHSCOPE_AVAILABLE = False


# --------------------------------------------------------------------------- #
# 1. Input handling (Agent B contract)                                        #
# --------------------------------------------------------------------------- #
def read_implementation_output(input_path):
    """Read Agent B output following schemas/implementation_output.json."""
    with open(input_path, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_implementation_output(impl):
    """Validate the Agent B contract before we try to test it."""
    required = ["code", "filename", "language", "dependencies"]
    missing = [f for f in required if f not in impl]
    if missing:
        return False, f"Missing required fields: {missing}"
    if not isinstance(impl["code"], str):
        return False, "code must be a string"
    if not impl["filename"].endswith(".py"):
        return False, "filename must end with .py"
    if impl["language"].lower() != "python":
        return False, "Agent C currently only tests Python code"
    return True, "Agent B output is valid"


# --------------------------------------------------------------------------- #
# 2. Static analysis of the code under test                                   #
# --------------------------------------------------------------------------- #
def inspect_code(code):
    """
    Use ast to discover the primary class and its public methods so the test
    generator can target the real API instead of guessing.
    """
    tree = ast.parse(code)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    if not classes:
        return None
    cls = classes[0]
    methods = []
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            args = [a.arg for a in node.args.args if a.arg != "self"]
            methods.append({"name": node.name, "args": args})
    return {"class_name": cls.name, "methods": methods}


# --------------------------------------------------------------------------- #
# 3. Prompt construction (for the real Qwen path)                             #
# --------------------------------------------------------------------------- #
def build_test_prompt(impl, analysis=None):
    """Prompt Qwen to return ONLY a pytest module for the given code."""
    requirement_context = ""
    if analysis:
        requirement_context = (
            "Requirement context from Agent A:\n"
            + json.dumps(analysis, indent=2, ensure_ascii=False)
        )

    return f"""You are Agent C: Tester in an LLM-based Software Engineering Agent system.

You are given Python code produced by Agent B. Write a pytest test module for it.

Module filename produced by Agent B: {impl['filename']}
{requirement_context}

Code under test:
```python
{impl['code']}
```

Rules:
1. Return ONLY Python test code. No markdown fences, no prose.
2. Import the class from the module name without the .py extension.
3. Use @pytest.mark.parametrize for happy-path and edge cases.
4. Cover: happy path, duplicate/invalid input, not-found cases, and listing.
5. Use plain `assert`; do not write custom assertion helpers.
6. The file must pass ast.parse.
"""


# --------------------------------------------------------------------------- #
# 4. Mock test generator (deterministic fallback, fully runnable)             #
# --------------------------------------------------------------------------- #
def mock_generate_tests(impl):
    """
    Generate a real pytest module for an Agent-B CRUD manager class by
    discovering its methods. Mirrors the actual ProductManager / StudentManager
    shape: add_*/delete_*/update_*/search_*/list_* returning (bool, msg).
    """
    info = inspect_code(impl["code"])
    module = impl["filename"][:-3]  # strip .py
    if not info:
        # Fallback: smoke test that the module at least imports.
        return (
            "import importlib\n\n\n"
            f"def test_module_imports():\n"
            f"    importlib.import_module(\"{module}\")\n"
        )

    cls = info["class_name"]
    method_names = {m["name"]: m for m in info["methods"]}

    add = next((m for m in method_names if m.startswith("add_")), None)
    delete = next((m for m in method_names if m.startswith("delete_")), None)
    update = next((m for m in method_names if m.startswith("update_")), None)
    search = next((m for m in method_names if m.startswith("search_")), None)
    listm = next((m for m in method_names if m.startswith("list_")), None)

    add_args = method_names[add]["args"] if add else []
    # Build a sample positional argument tuple for add_*.
    sample = []
    for a in add_args:
        if "id" in a:
            sample.append('"X001"')
        elif "name" in a:
            sample.append('"Sample"')
        elif "price" in a:
            sample.append("9.99")
        elif "stock" in a or "age" in a:
            sample.append("5")
        else:
            sample.append('"value"')
    sample_args = ", ".join(sample)
    first_id = sample[0] if sample else '"X001"'

    lines = []
    lines.append("import pytest")
    lines.append(f"from {module} import {cls}")
    lines.append("")
    lines.append("")
    lines.append("@pytest.fixture")
    lines.append("def manager():")
    lines.append(f"    return {cls}()")
    lines.append("")
    lines.append("")

    if add:
        lines.append(f"def test_{add}_happy_path(manager):")
        lines.append(f"    ok, msg = manager.{add}({sample_args})")
        lines.append("    assert ok is True")
        lines.append("    assert isinstance(msg, str)")
        lines.append("")
        lines.append("")
        lines.append(f"def test_{add}_duplicate_rejected(manager):")
        lines.append(f"    manager.{add}({sample_args})")
        lines.append(f"    ok, msg = manager.{add}({sample_args})")
        lines.append("    assert ok is False")
        lines.append("")
        lines.append("")

    if search and add:
        lines.append(f"def test_{search}_found(manager):")
        lines.append(f"    manager.{add}({sample_args})")
        lines.append(f"    result = manager.{search}({first_id})")
        lines.append("    assert result is not None")
        lines.append("")
        lines.append("")
        lines.append(f"def test_{search}_not_found_returns_none(manager):")
        lines.append(f"    assert manager.{search}(\"DOES_NOT_EXIST\") is None")
        lines.append("")
        lines.append("")

    if delete and add:
        lines.append(f"def test_{delete}_existing(manager):")
        lines.append(f"    manager.{add}({sample_args})")
        lines.append(f"    ok, msg = manager.{delete}({first_id})")
        lines.append("    assert ok is True")
        lines.append("")
        lines.append("")
        lines.append(f"def test_{delete}_missing_rejected(manager):")
        lines.append(f"    ok, msg = manager.{delete}(\"DOES_NOT_EXIST\")")
        lines.append("    assert ok is False")
        lines.append("")
        lines.append("")

    if update and add:
        lines.append(f"def test_{update}_missing_rejected(manager):")
        lines.append(f"    ok, msg = manager.{update}(\"DOES_NOT_EXIST\")")
        lines.append("    assert ok is False")
        lines.append("")
        lines.append("")

    if listm and add:
        lines.append("@pytest.mark.parametrize(\"count\", [0, 1, 2])")
        lines.append(f"def test_{listm}_count(manager, count):")
        lines.append("    for i in range(count):")
        # add unique ids
        if len(sample) >= 1:
            rest = ", ".join(sample[1:]) if len(sample) > 1 else ""
            rest = (", " + rest) if rest else ""
            lines.append(
                f"        manager.{add}(f\"ID{{i}}\"{rest})"
            )
        lines.append(f"    assert len(manager.{listm}()) == count")
        lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 5. Qwen path (optional, falls back to mock)                                 #
# --------------------------------------------------------------------------- #
def extract_code_from_text(text):
    text = text.strip()
    text = re.sub(r"^```python", "", text)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)
    return text.strip()


def patch_missing_imports(test_code):
    """Add missing stdlib imports that Qwen commonly forgets."""
    stdlib_checks = [
        ("time", r"\btime\s*\."),
        ("datetime", r"\bdatetime\s*\."),
        ("os", r"\bos\s*\."),
        ("sys", r"\bsys\s*\."),
        ("json", r"\bjson\s*\."),
        ("re", r"\bre\s*\."),
        ("random", r"\brandom\s*\."),
        ("string", r"\bstring\s*\."),
        ("hashlib", r"\bhashlib\s*\."),
    ]
    lines = test_code.splitlines()
    existing = {l.strip() for l in lines if l.startswith("import ") or l.startswith("from ")}
    to_add = []
    for module, pattern in stdlib_checks:
        if re.search(pattern, test_code) and f"import {module}" not in existing:
            to_add.append(f"import {module}")
    if not to_add:
        return test_code
    return "\n".join(to_add) + "\n" + test_code


def qwen_generate_tests(impl, analysis=None):
    if not _DASHSCOPE_AVAILABLE:
        raise RuntimeError("dashscope not installed")
    load_dotenv()
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY is missing. Check your .env file.")
    dashscope.api_key = api_key
    dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
    prompt = build_test_prompt(impl, analysis)
    response = dashscope.Generation.call(model="qwen-max", prompt=prompt)
    if response.status_code != 200:
        raise RuntimeError(f"Qwen call failed: {response.code} - {response.message}")
    content = response.output.get("text") or (
        response.output["choices"][0]["message"]["content"]
    )
    return extract_code_from_text(content)


# --------------------------------------------------------------------------- #
# 6. Sandbox runner  (relocated to the `sandbox` package in M5 Week 4)        #
# --------------------------------------------------------------------------- #
# The runner now lives in sandbox/ so it can route between Docker-isolated
# execution and the subprocess fallback. Re-exported here so existing imports
# (`from agents.agent_c.agent_c_tester import run_tests_in_sandbox`) keep working.
from sandbox.sandbox_runner import run_tests_in_sandbox  # noqa: E402,F401


# --------------------------------------------------------------------------- #
# 7. Main workflow                                                            #
# --------------------------------------------------------------------------- #
def run_agent_c(input_path, output_dir, analysis_path=None):
    impl = read_implementation_output(input_path)

    valid, msg = validate_implementation_output(impl)
    if not valid:
        return {"success": False, "stage": "validate_input", "message": msg}

    analysis = None
    if analysis_path and os.path.exists(analysis_path):
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis = json.load(f)

    # Generate tests: try Qwen, fall back to deterministic mock.
    mode = "qwen_api"
    retry_used = False
    retry_reason = "none"
    try:
        test_code = qwen_generate_tests(impl, analysis)
        test_code = patch_missing_imports(test_code)
    except Exception as error:  # noqa: BLE001
        test_code = mock_generate_tests(impl)
        mode = "mock_generator_fallback"
        retry_used = True
        retry_reason = f"qwen_unavailable_fallback_to_mock: {error}"

    # Validate generated test syntax.
    try:
        ast.parse(test_code)
        syntax_check = "passed"
    except SyntaxError as error:
        syntax_check = f"failed: {error}"
        if mode == "qwen_api":
            test_code = mock_generate_tests(impl)
            retry_used = True
            retry_reason = "qwen_test_syntax_error_fallback_to_mock"
            mode = "mock_generator_fallback"
            ast.parse(test_code)
            syntax_check = "passed"

    # Run in sandbox.
    run_result = run_tests_in_sandbox(
        impl["code"], test_code, impl["filename"]
    )

    os.makedirs(output_dir, exist_ok=True)
    test_file_path = os.path.join(output_dir, "test_generated.py")
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_code)

    test_output = {
        "tested_file": impl["filename"],
        "language": impl["language"],
        "test_code": test_code,
        "test_file": test_file_path,
        "syntax_check": syntax_check,
        "mode": mode,
        "retry_used": retry_used,
        "retry_reason": retry_reason,
        "execution": run_result,
        "summary": {
            "passed": run_result.get("passed", 0),
            "failed": run_result.get("failed", 0),
            "total": run_result.get("total", 0),
        },
    }

    output_json_path = os.path.join(output_dir, "test_output.json")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(test_output, f, indent=4, ensure_ascii=False)

    return {
        "success": run_result.get("executed", False)
        and run_result.get("failed", 1) == 0,
        "message": "Agent C test generation finished",
        "input_schema": "schemas/implementation_output.json",
        "output_schema": "schemas/test_output.json",
        "test_output_json": output_json_path,
        "test_file": test_file_path,
        "mode": mode,
        "retry_used": retry_used,
        "retry_reason": retry_reason,
        "syntax_check": syntax_check,
        "tests_passed": run_result.get("passed", 0),
        "tests_failed": run_result.get("failed", 0),
        "tests_total": run_result.get("total", 0),
    }


if __name__ == "__main__":
    in_path = sys.argv[1] if len(sys.argv) > 1 else "outputs/implementation_output.json"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "outputs"
    result = run_agent_c(in_path, out_dir)
    print(json.dumps(result, indent=4, ensure_ascii=False))
