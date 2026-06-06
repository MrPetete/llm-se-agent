"""Schema sanity tests for Agent C output (mirrors M3's schema test style)."""
import json
from pathlib import Path


def test_test_output_schema_fields():
    schema = json.loads(
        Path("schemas/test_output.json").read_text(encoding="utf-8")
    )
    assert schema["title"] == "TestOutput"
    for field in ["tested_file", "language", "test_code", "summary", "execution"]:
        assert field in schema["required"]
