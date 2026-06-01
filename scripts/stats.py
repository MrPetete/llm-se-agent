# scripts/stats.py
"""Aggregate logs/llm_calls.jsonl into a human-readable usage summary.

Reads every logged LLM call and prints totals plus a per-agent breakdown.
Designed for M6 (docs — total tokens) and M7 (QA — per-agent split).

Fields are read defensively with .get() because early log lines (Week 1)
predate the `agent` and `provider` fields added later in llm/logging_.py.
"""
import json
from collections import defaultdict
from pathlib import Path

LOG_PATH = Path("logs/llm_calls.jsonl")


def load_calls(log_path: Path = LOG_PATH):
    """Return a list of call dicts, skipping any malformed lines."""
    if not log_path.exists():
        return []
    calls = []
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                calls.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # skip a corrupt/partial line rather than crash
    return calls


def summarize(calls):
    """Compute totals and a per-agent breakdown from a list of call dicts."""
    total_calls = len(calls)
    total_tokens = sum((c.get("total_tokens") or 0) for c in calls)
    total_time = sum((c.get("elapsed_seconds") or 0) for c in calls)

    by_agent = defaultdict(lambda: {"calls": 0, "tokens": 0, "time": 0.0})
    for c in calls:
        agent = c.get("agent") or "untagged"
        by_agent[agent]["calls"] += 1
        by_agent[agent]["tokens"] += c.get("total_tokens") or 0
        by_agent[agent]["time"] += c.get("elapsed_seconds") or 0

    return total_calls, total_tokens, total_time, by_agent


def render(calls) -> str:
    """Build the printable summary string (separated for testability)."""
    if not calls:
        return "No LLM calls logged yet (logs/llm_calls.jsonl is empty or missing)."

    total_calls, total_tokens, total_time, by_agent = summarize(calls)
    avg_time = total_time / total_calls if total_calls else 0

    lines = []
    lines.append("=" * 52)
    lines.append(" LLM Usage Summary")
    lines.append("=" * 52)
    lines.append(f" Total calls       : {total_calls}")
    lines.append(f" Total tokens      : {total_tokens:,}")
    lines.append(f" Total time        : {total_time:.1f}s")
    lines.append(f" Avg time per call : {avg_time:.2f}s")
    lines.append("-" * 52)
    lines.append(f" {'Agent':<12}{'Calls':>8}{'Tokens':>14}{'Time(s)':>14}")
    lines.append("-" * 52)
    for agent in sorted(by_agent):
        s = by_agent[agent]
        lines.append(f" {agent:<12}{s['calls']:>8}{s['tokens']:>14,}{s['time']:>14.1f}")
    lines.append("=" * 52)
    return "\n".join(lines)


def main():
    print(render(load_calls()))


if __name__ == "__main__":
    main()
