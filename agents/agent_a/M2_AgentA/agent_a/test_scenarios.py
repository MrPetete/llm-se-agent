"""
Agent A: Test Scenarios
=======================
5+ test scenarios for validating the Requirements Analyst agent.
Each scenario tests different aspects of PRD generation.
"""

from typing import Dict, Any

TEST_SCENARIOS = [
    {
        "id": "T1",
        "name": "Simple Mobile App",
        "description": "Basic to-do list app - tests fundamental PRD generation",
        "input": """
        I want a simple to-do list app where I can add tasks, mark them complete,
        and delete them. It should save my tasks so they're still there when I
        open the app again.
        """,
        "expected_outputs": {
            "min_features": 3,
            "min_functional_requirements": 4,
            "must_have_user_types": ["users", "individual users"],
        },
        "validation_criteria": [
            "PRD includes task CRUD operations (Create, Read, Update, Delete)",
            "Persistence requirement is explicitly stated",
            "Success metrics include user retention or task completion rate",
        ],
    },
    {
        "id": "T2",
        "name": "E-commerce Platform",
        "description": "Online store - tests handling of complex business logic",
        "input": """
        Build an e-commerce website for selling vintage books. Users should be able
        to browse books by category, add to cart, checkout with payment, and track
        their orders. Sellers need a dashboard to manage inventory.
        """,
        "expected_outputs": {
            "min_features": 5,
            "min_functional_requirements": 8,
            "must_have_user_types": ["buyers", "sellers", "customers"],
        },
        "validation_criteria": [
            "Payment security requirements are specified",
            "Both buyer and seller user types are identified",
            "Order tracking flow is described",
            "Non-functional requirements include security and reliability",
        ],
    },
    {
        "id": "T3",
        "name": "Real-time Chat Application",
        "description": "Messaging app - tests real-time and concurrency requirements",
        "input": """
        I need a chat application where team members can send instant messages,
        create group channels, share files, and see who's online. Messages should
        appear instantly and support emojis and reactions.
        """,
        "expected_outputs": {
            "min_features": 5,
            "min_functional_requirements": 6,
            "must_have_non_functional": ["performance", "real-time"],
        },
        "validation_criteria": [
            "Real-time performance requirement has specific latency target",
            "File sharing includes size limits and supported formats",
            "Presence detection is specified (how quickly online status updates)",
        ],
    },
    {
        "id": "T4",
        "name": "Data Analytics Dashboard",
        "description": "Business intelligence tool - tests data visualization requirements",
        "input": """
        Create a dashboard for business analysts to view sales data. It should
        connect to our database, display charts and graphs, allow filtering by
        date range and region, and export reports to PDF and Excel.
        """,
        "expected_outputs": {
            "min_features": 4,
            "min_functional_requirements": 6,
            "must_have_user_types": ["analysts", "business users"],
        },
        "validation_criteria": [
            "Database connection requirements specify supported databases",
            "Export formats are explicitly listed (PDF, Excel)",
            "Performance requirements for query response time",
            "Data refresh frequency is specified",
        ],
    },
    {
        "id": "T5",
        "name": "Fitness Tracking App",
        "description": "Health app - tests integration with external services",
        "input": """
        Build a fitness app that tracks workouts, counts steps, monitors heart rate,
        and syncs with Apple Health and Google Fit. Users should set goals, see
        progress charts, and get achievement badges when they hit milestones.
        """,
        "expected_outputs": {
            "min_features": 6,
            "min_functional_requirements": 8,
            "external_integrations": ["Apple Health", "Google Fit"],
        },
        "validation_criteria": [
            "External API integration requirements are specified",
            "Data privacy requirements for health data (HIPAA consideration)",
            "Goal-setting includes measurable targets",
            "Achievement system has clear trigger conditions",
        ],
    },
    {
        "id": "T6",
        "name": "Ambiguous Request (Edge Case)",
        "description": "Vague input - tests handling of underspecified requirements",
        "input": """
        I want something like Uber but for pet sitting. You know, connect people
        who need help with people who can help. Make it work smoothly.
        """,
        "expected_outputs": {
            "min_features": 4,
            "assumptions_documented": True,
        },
        "validation_criteria": [
            "Agent makes reasonable assumptions explicit in output",
            "Identifies both service providers and seekers as user types",
            "Trust/safety requirements are addressed (background checks, reviews)",
            "Payment flow is specified even though not explicitly requested",
        ],
    },
    {
        "id": "T7",
        "name": "Over-specified Enterprise Request",
        "description": "Too much scope - tests appropriate scoping for student project",
        "input": """
        Build a complete hospital management system with patient records, doctor
        scheduling, pharmacy inventory, billing, insurance claims, lab results,
        telemedicine video calls, mobile apps for iOS and Android, integration
        with every major hospital chain, AI diagnosis support, and blockchain
        for secure records. It must be HIPAA compliant and support 1 million
        concurrent users globally.
        """,
        "expected_outputs": {
            "should_scope_down": True,
            "mvp_features_identified": True,
        },
        "validation_criteria": [
            "Agent identifies this is too large for a student project",
            "Suggests an MVP subset of features",
            "Still provides complete PRD structure but with phased approach",
            "HIPAA compliance is prominently featured in non-functional requirements",
        ],
    },
]


def validate_prd_output(prd: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate PRD output against expected criteria.

    Returns:
        {"passed": bool, "details": str}
    """
    details = []
    passed = True

    # Check minimum features
    if "min_features" in scenario["expected_outputs"]:
        actual_features = len(prd.get("core_features", []))
        expected = scenario["expected_outputs"]["min_features"]
        if actual_features >= expected:
            details.append(f"✓ Features: {actual_features} >= {expected}")
        else:
            details.append(f"✗ Features: {actual_features} < {expected}")
            passed = False

    # Check functional requirements
    if "min_functional_requirements" in scenario["expected_outputs"]:
        actual_fr = len(prd.get("functional_requirements", []))
        expected = scenario["expected_outputs"]["min_functional_requirements"]
        if actual_fr >= expected:
            details.append(f"✓ Functional Requirements: {actual_fr} >= {expected}")
        else:
            details.append(f"✗ Functional Requirements: {actual_fr} < {expected}")
            passed = False

    # Check user types
    if "must_have_user_types" in scenario["expected_outputs"]:
        target_users = " ".join(prd.get("target_users", [])).lower()
        for required in scenario["expected_outputs"]["must_have_user_types"]:
            if required.lower() in target_users:
                details.append(f"✓ User type found: {required}")
            else:
                details.append(f"✗ Missing user type: {required}")
                passed = False

    return {"passed": passed, "details": "\n".join(details)}


if __name__ == "__main__":
    # Print test scenario summary
    print("Agent A Test Scenarios")
    print("=" * 50)
    for scenario in TEST_SCENARIOS:
        print(f"\n{scenario['id']}: {scenario['name']}")
        print(f"  Description: {scenario['description']}")
        print(f"  Input (truncated): {scenario['input'][:80]}...")
        print(f"  Validation: {len(scenario['validation_criteria'])} criteria")
