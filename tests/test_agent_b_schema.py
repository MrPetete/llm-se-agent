import json
from pathlib import Path


def test_agent_b_sample_input_schema():
    input_path = Path("tests/agent_b_sample_input.json")
    assert input_path.exists()

    data = json.loads(input_path.read_text(encoding="utf-8"))

    required_fields = [
        "requirement_summary",
        "components",
        "design_plan",
        "dependencies",
    ]

    for field in required_fields:
        assert field in data


def test_agent_b_sample_output_schema():
    output_path = Path("tests/agent_b_sample_output.json")
    assert output_path.exists()

    data = json.loads(output_path.read_text(encoding="utf-8"))

    required_fields = [
        "code",
        "filename",
        "language",
        "dependencies",
    ]

    for field in required_fields:
        assert field in data

    assert data["language"] == "python"
    assert data["filename"].endswith(".py")
    assert isinstance(data["dependencies"], list)