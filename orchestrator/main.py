from dotenv import load_dotenv
import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from agents.agent_a.requirements_analyst import RequirementsAnalyst
from agents.agent_b.agent_b_implementation import run_agent_b
from agents.agent_c.agent_c_tester import run_agent_c
from agents.agent_c.agent_c_debugger import run_agent_c_debugger
from llm.observability import setup, set_agent

load_dotenv()


def run_pipeline(user_input: str, output_dir: str = "outputs", run_test: bool = True) -> str:
    """Run the full A -> B -> C pipeline for a given user requirement.

    Args:
        user_input: Plain-English description of the software to build.
        output_dir: Directory for all stage JSON artifacts.
        run_test: When False, stages 3 & 4 (Agent C tester + debugger) are skipped.

    Stage 1: M2's real RequirementsAnalyst  -> {output_dir}/analysis_output.json
    Stage 2: M3's real Agent B              -> {output_dir}/implementation_output.json
    Stage 3: M4's real Agent C tester       -> {output_dir}/test_output.json
    Stage 4: M4's real Agent C debugger     -> {output_dir}/debug_output.json
    """
    os.makedirs(output_dir, exist_ok=True)
    analysis_path = os.path.join(output_dir, "analysis_output.json")
    implementation_path = os.path.join(output_dir, "implementation_output.json")
    test_path = os.path.join(output_dir, "test_output.json")

    setup()

    # ── Stage 1: M2's real Agent A ──
    print("\n===== STAGE 1: AGENT A (Requirements Analysis) =====")
    set_agent("agent_a")
    analyst = RequirementsAnalyst()
    analysis = analyst.analyze(user_input)

    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=4, ensure_ascii=False)
    print(f"Agent A output saved -> {analysis_path}")

    # ── Stage 2: M3's real Agent B ──
    print("\n===== STAGE 2: AGENT B (Code Generation) =====")
    set_agent("agent_b")
    b_result = run_agent_b(analysis_path, output_dir)
    if not b_result.get("success"):
        print(f"Agent B failed: {b_result.get('message')}")
    else:
        print(f"Agent B output saved -> {b_result.get('implementation_json')}")
        print(f"Mode: {b_result.get('mode')} | Syntax: {b_result.get('syntax_check')}")

    if not run_test:
        print("\n===== STAGES 3 & 4 SKIPPED (--no-test) =====")
        return json.dumps({
            "agent_b": {
                "mode": b_result.get("mode"),
                "filename": b_result.get("filename"),
                "syntax_check": b_result.get("syntax_check"),
            },
            "agent_c_tester": None,
            "agent_c_debugger": None,
        }, indent=2, ensure_ascii=False)

    # ── Stage 3: M4's real Agent C tester ──
    print("\n===== STAGE 3: AGENT C (Test Generation) =====")
    set_agent("agent_c")
    c_result = run_agent_c(
        implementation_path,
        output_dir,
        analysis_path=analysis_path,
    )
    if not c_result.get("success"):
        print(f"Agent C tester: some tests failed (mode: {c_result.get('mode')})")
    else:
        print(f"Agent C tester finished -> {test_path}")
    print(f"Mode: {c_result.get('mode')} | Tests: {c_result.get('tests_passed')} passed, {c_result.get('tests_failed')} failed")

    # ── Stage 4: M4's real Agent C debugger ──
    print("\n===== STAGE 4: AGENT C (Debugger) =====")
    set_agent("agent_c_debugger")
    d_result = run_agent_c_debugger(test_path, output_dir)
    status = d_result.get("status")
    verified = d_result.get("verified", False)
    print(f"Debugger status: {status} | Verified: {verified}")
    if d_result.get("fix_attempted"):
        before = d_result.get("before", {})
        after = d_result.get("after", {})
        print(f"Before fix: {before.get('passed')} passed / {before.get('failed')} failed")
        print(f"After fix:  {after.get('passed')} passed / {after.get('failed')} failed")

    return json.dumps({
        "agent_b": {
            "mode": b_result.get("mode"),
            "filename": b_result.get("filename"),
            "syntax_check": b_result.get("syntax_check"),
        },
        "agent_c_tester": {
            "mode": c_result.get("mode"),
            "tests_passed": c_result.get("tests_passed"),
            "tests_failed": c_result.get("tests_failed"),
            "tests_total": c_result.get("tests_total"),
        },
        "agent_c_debugger": {
            "status": status,
            "verified": verified,
            "mode": d_result.get("mode"),
            "applied_fixes": d_result.get("applied_fixes", []),
        },
    }, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    user_input = input("Enter your software requirement: ")
    result = run_pipeline(user_input)
    print("\n===== FINAL OUTPUT =====")
    print(result)
