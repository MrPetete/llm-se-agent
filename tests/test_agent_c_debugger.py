"""
Unit tests for Agent C's debugger (Week 3 deliverable).

Covers two things the Week 3 report claims:
  1. The traceback categorizer assigns the correct root-cause category
     across the common pytest failure types.
  2. The debug_output.json schema declares the fields the debugger emits.

Style mirrors tests/test_agent_c_schema.py (M4's Week 2 schema test).
"""
import json
from pathlib import Path

import pytest

from agents.agent_c.agent_c_debugger import categorize_failure, analyze_failures


# --------------------------------------------------------------------------- #
# 1. Traceback categorization                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "traceback, expected",
    [
        ("E   TypeError: cannot unpack non-iterable bool object", "TypeError"),
        ("E   ModuleNotFoundError: No module named 'product_manager'", "ImportError"),
        ("E   ImportError: cannot import name 'ProductManager'", "ImportError"),
        ("E   AttributeError: 'ProductManager' object has no attribute 'add_item'", "AttributeError"),
        ("E   NameError: name 'foo' is not defined", "NameError"),
        ("E   KeyError: 'X001'", "KeyError"),
        ("E   IndexError: list index out of range", "IndexError"),
        ("E   assert False is True\nE   AssertionError", "AssertionError"),
        ("ERROR collecting test_generated.py", "collection_error"),
        ("E   ValueError: something unexpected", "runtime_error"),
    ],
)
def test_categorize_failure_assigns_expected_category(traceback, expected):
    category, explanation = categorize_failure(traceback)
    assert category == expected
    assert isinstance(explanation, str) and explanation


def test_analyze_failures_preserves_test_id_and_adds_category():
    failures = [
        {
            "test": "test_generated.py::test_add_product_happy_path",
            "outcome": "failed",
            "traceback_summary": "E   TypeError: cannot unpack non-iterable bool object",
        }
    ]
    analyzed = analyze_failures(failures)
    assert len(analyzed) == 1
    item = analyzed[0]
    assert item["test"] == "test_generated.py::test_add_product_happy_path"
    assert item["category"] == "TypeError"
    assert "explanation" in item


def test_analyze_failures_handles_empty_list():
    assert analyze_failures([]) == []


# --------------------------------------------------------------------------- #
# 2. Schema sanity                                                            #
# --------------------------------------------------------------------------- #
def test_debug_output_schema_fields():
    schema = json.loads(
        Path("schemas/debug_output_schema.json").read_text(encoding="utf-8")
    )
    assert schema["title"] == "DebugOutput"
    for field in ["status", "tested_file", "analysis", "fix_attempted", "verified"]:
        assert field in schema["required"]


# --------------------------------------------------------------------------- #
# 3. Test-side repair (collection errors are bugs in the generated TEST,      #
#    not in the code under test). Regression for the Week 4 fix_unverified    #
#    0/1 -> 0/1 stall reported by M3 in the Stage-4 screenshot.               #
# --------------------------------------------------------------------------- #
from agents.agent_c.agent_c_debugger import (  # noqa: E402
    _failure_is_test_side,
    repair_test_code,
)


def test_collection_error_is_classified_test_side():
    analyzed = [{
        "test": "test_generated.py",
        "outcome": "error",
        "category": "collection_error",
        "explanation": "x",
        "traceback_summary": "ERROR collecting test_generated.py",
    }]
    assert _failure_is_test_side(analyzed) is True


def test_assertion_error_is_not_test_side():
    analyzed = [{
        "test": "t::test_logic", "outcome": "failed", "category": "AssertionError",
        "explanation": "x", "traceback_summary": "E assert 1 == 2",
    }]
    assert _failure_is_test_side(analyzed) is False


def test_repair_test_code_injects_missing_mock_and_stdlib_imports():
    broken = (
        "import pytest\n"
        "from login_system import UserDatabase\n\n"
        "@patch('login_system.UserDatabase._hash')\n"
        "def test_login(mock_hash):\n"
        "    mock_hash.return_value = hashlib.sha256(b'pw').hexdigest()\n"
        "    assert True\n"
    )
    fixed, applied = repair_test_code(broken, "login_system.py")
    assert "from unittest.mock import" in fixed
    assert "import hashlib" in fixed
    assert "sys.path.insert" in fixed
    assert applied  # something was recorded
    # the repaired test module must still parse
    import ast
    ast.parse(fixed)


def test_repair_test_code_is_idempotent_on_clean_test():
    clean = (
        "import pytest\n"
        "from product_manager import ProductManager\n\n"
        "def test_add(): \n"
        "    assert ProductManager() is not None\n"
    )
    fixed, applied = repair_test_code(clean, "product_manager.py")
    # No mock / no missing stdlib; only the sys.path bootstrap may be added.
    assert all("unittest.mock" not in a for a in applied)
