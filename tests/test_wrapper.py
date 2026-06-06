# tests/test_wrapper.py
"""
Smoke test for llm/wrapper.py
Requires a real DASHSCOPE_API_KEY in .env to pass.
Run with:  pytest tests/test_wrapper.py -v
"""
import pytest
from llm.wrapper import ask


def test_ask_returns_string():
    """ask() should return a non-empty string."""
    result = ask("Reply with exactly the word: HELLO")
    assert isinstance(result, str)
    assert len(result) > 0


def test_ask_with_system_prompt():
    """ask() should accept an optional system prompt."""
    result = ask(
        prompt="What is 2 + 2?",
        system="You are a helpful math tutor. Keep answers brief.",
    )
    assert "4" in result


def test_ask_default_model():
    """Default model should be qwen-max (smoke test only — checks no crash)."""
    result = ask("Say 'OK' and nothing else.")
    assert isinstance(result, str)