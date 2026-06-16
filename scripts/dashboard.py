"""scripts/dashboard.py — LLM call metrics dashboard (M5).

Run with:
    streamlit run scripts/dashboard.py

Reads logs/llm_calls.jsonl and visualises usage metrics.
Handles both old log format (Week 1, no provider/agent/success fields)
and new format (Week 2+, full fields).
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

LOG_PATH = Path("logs/llm_calls.jsonl")

st.set_page_config(page_title="LLM Usage Dashboard", layout="wide")
st.title("LLM Usage Dashboard")
st.caption("Source: logs/llm_calls.jsonl — auto-refreshes on reload")


# ── Load ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=10)
def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["agent"] = df.get("agent", pd.Series(dtype=str)).fillna("untagged")
    df["provider"] = df.get("provider", pd.Series(dtype=str)).fillna("unknown")
    df["success"] = df.get("success", pd.Series(dtype=object)).fillna(True).astype(bool)
    df["total_tokens"] = df["total_tokens"].fillna(0).astype(int)
    df["prompt_tokens"] = df["prompt_tokens"].fillna(0).astype(int)
    df["completion_tokens"] = df["completion_tokens"].fillna(0).astype(int)
    df["elapsed_seconds"] = df["elapsed_seconds"].fillna(0.0)
    return df.sort_values("timestamp")


df = load_data(LOG_PATH)

if df.empty:
    st.warning("No log data found. Run the pipeline first, then reload this page.")
    st.stop()

# ── Sidebar filters ───────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Filters")
    agents = ["All"] + sorted(df["agent"].unique().tolist())
    selected_agent = st.selectbox("Agent", agents)
    models = ["All"] + sorted(df["model"].unique().tolist())
    selected_model = st.selectbox("Model", models)

filtered = df.copy()
if selected_agent != "All":
    filtered = filtered[filtered["agent"] == selected_agent]
if selected_model != "All":
    filtered = filtered[filtered["model"] == selected_model]

# ── Top metrics ───────────────────────────────────────────────────────────────

total_calls = len(filtered)
total_tokens = int(filtered["total_tokens"].sum())
failed_calls = int((~filtered["success"].astype(bool)).sum())
avg_latency = filtered["elapsed_seconds"].mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Calls", total_calls)
c2.metric("Total Tokens", f"{total_tokens:,}")
c3.metric("Failed Calls", failed_calls)
c4.metric("Avg Latency (s)", f"{avg_latency:.2f}")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────

left, right = st.columns(2)

with left:
    st.subheader("Tokens per Agent")
    by_agent = (
        filtered.groupby("agent")["total_tokens"]
        .sum()
        .reset_index()
        .rename(columns={"total_tokens": "tokens"})
    )
    fig = px.bar(by_agent, x="agent", y="tokens", text_auto=True,
                 labels={"agent": "Agent", "tokens": "Total Tokens"})
    fig.update_layout(showlegend=False, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Calls over Time")
    calls_over_time = (
        filtered.set_index("timestamp")
        .resample("1min")["total_tokens"]
        .count()
        .reset_index()
        .rename(columns={"total_tokens": "calls"})
    )
    fig2 = px.line(calls_over_time, x="timestamp", y="calls",
                   labels={"timestamp": "Time", "calls": "Calls"})
    fig2.update_layout(margin=dict(t=20))
    st.plotly_chart(fig2, use_container_width=True)

left2, right2 = st.columns(2)

with left2:
    st.subheader("Latency Distribution (s)")
    fig3 = px.histogram(filtered, x="elapsed_seconds", nbins=20,
                        labels={"elapsed_seconds": "Latency (s)"})
    fig3.update_layout(margin=dict(t=20))
    st.plotly_chart(fig3, use_container_width=True)

with right2:
    st.subheader("Prompt vs Completion Tokens")
    token_melt = filtered[["agent", "prompt_tokens", "completion_tokens"]].copy()
    token_melt = token_melt.groupby("agent")[["prompt_tokens", "completion_tokens"]].sum().reset_index()
    token_melt = token_melt.melt(id_vars="agent", var_name="type", value_name="tokens")
    fig4 = px.bar(token_melt, x="agent", y="tokens", color="type", barmode="group",
                  labels={"agent": "Agent", "tokens": "Tokens", "type": "Type"})
    fig4.update_layout(margin=dict(t=20))
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ── Per-agent breakdown table ─────────────────────────────────────────────────

st.subheader("Per-Agent Breakdown")
breakdown = (
    filtered.groupby("agent")
    .agg(
        calls=("total_tokens", "count"),
        total_tokens=("total_tokens", "sum"),
        prompt_tokens=("prompt_tokens", "sum"),
        completion_tokens=("completion_tokens", "sum"),
        avg_latency_s=("elapsed_seconds", "mean"),
        failed=("success", lambda x: (~x).sum()),
    )
    .reset_index()
    .sort_values("total_tokens", ascending=False)
)
breakdown["avg_latency_s"] = breakdown["avg_latency_s"].round(2)
st.dataframe(breakdown, use_container_width=True, hide_index=True)

# ── Raw log ───────────────────────────────────────────────────────────────────

with st.expander("Raw log entries"):
    st.dataframe(
        filtered[["timestamp", "agent", "model", "provider",
                  "total_tokens", "elapsed_seconds", "success", "prompt_preview"]]
        .sort_values("timestamp", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
