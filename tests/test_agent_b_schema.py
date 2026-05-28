import json
from pathlib import Path


def test_agent_b_sample_input_schema():
    input_path = Path("tests/agent_b_sample_input.json")
    assert input_path.exists()

    data = json.loads(input_path.read_text(encoding="utf-8"))

    required_fields = [
        "prd",
        "user_stories",
        "architecture_outline",
    ]

    for field in required_fields:
        assert field in data

    assert isinstance(data["prd"], dict)
    assert isinstance(data["user_stories"], list)
    assert isinstance(data["architecture_outline"], dict)

    prd_required_fields = [
        "product_overview",
        "core_features",
        "functional_requirements",
    ]

    for field in prd_required_fields:
        assert field in data["prd"]

    assert isinstance(data["prd"]["product_overview"], str)
    assert isinstance(data["prd"]["core_features"], list)
    assert isinstance(data["prd"]["functional_requirements"], list)


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