# orchestrator/pipeline.py
"""Non-interactive entry point that lets the CLI drive M1's agent crew.

M5-owned glue code. M1's `orchestrator/main.py` only runs via an interactive
`input()` prompt, so it cannot be called programmatically from run.py. This
module wraps M1's existing `crew` object in a plain function the CLI can call
with arguments.

Design notes:
- M1's `crew` is imported *inside* run_pipeline(), not at module top level.
  Importing orchestrator.main constructs a live LLM() client and the Crew as a
  side effect; keeping the import lazy means `import orchestrator.pipeline`
  stays cheap and side-effect-free (and works even where crewai is absent).
- Output is written to a timestamped subfolder under ``outputs/`` to avoid run
  collisions (a Week 3 risk flagged in the M5 handoff). ``outputs/`` matches the
  directory already ignored in the repo .gitignore, so run artifacts stay out of
  git automatically.
- This does NOT reimplement M1's agents — it reuses them. If M1 later adds an
  official run_pipeline() to main.py, this file can be deleted or thinned.
"""
import json
from datetime import datetime
from pathlib import Path


def run_pipeline(prompt: str, output_dir: str = "./outputs", run_test: bool = True) -> dict:
    """Run the full agent pipeline for a plain-English prompt.

    Args:
        prompt: Plain-English description of the software to build.
        output_dir: Base directory for output; a timestamped subfolder is created.
        run_test: Whether the testing agent (Agent C) should run. Currently
            advisory only — passed through to the run summary until M4/M1 wire
            a way to skip the test stage in the crew.

    Returns:
        dict with keys: "result" (final output text) and "run_dir" (path written).
    """
    # Lazy import: constructing the crew is a side effect we only want at call time.
    from orchestrator.main import crew

    result = crew.kickoff(inputs={"user_input": prompt})

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_dir = Path(output_dir) / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    output_text = str(result)
    (run_dir / "result.txt").write_text(output_text, encoding="utf-8")

    summary = {
        "prompt": prompt,
        "output_dir": str(run_dir),
        "run_test": run_test,
        "timestamp": stamp,
    }
    (run_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {"result": output_text, "run_dir": str(run_dir)}
