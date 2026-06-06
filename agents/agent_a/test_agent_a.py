"""
Quick test script for Agent A - Requirements Analyst
Run this to verify Week 4 functionality is working.
"""

import os
import json
from requirements_analyst import RequirementsAnalyst

# Check for API key
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("ERROR: DASHSCOPE_API_KEY not set!")
    print("Please set it with: set DASHSCOPE_API_KEY=your_key_here")
    exit(1)

print("=" * 60)
print("Agent A - Requirements Analyst (Week 4) Test")
print("=" * 60)

# Test input
test_input = """
I want to build a simple blog platform where writers can publish articles,
readers can comment and like posts, and admins can moderate content.
It should have user authentication and a clean reading interface.
"""

print("\nInput:")
print(test_input)
print("\n" + "=" * 60)
print("Running analysis... (this may take 1-2 minutes)")
print("=" * 60 + "\n")

try:
    # Initialize and run
    analyst = RequirementsAnalyst()
    result = analyst.analyze(test_input)

    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print("\n1. PRD (Product Overview):")
    print(f"   {result['prd']['product_overview'][:150]}...")
    print(f"   Target Users: {result['prd']['target_users']}")
    print(f"   Core Features: {len(result['prd']['core_features'])} features")
    print(f"   Validation Passed: {result['prd'].get('validation_passed', 'N/A')}")

    print("\n2. User Stories:")
    for i, story in enumerate(result['user_stories'][:3], 1):
        print(f"   {i}. {story['story'][:80]}...")

    print("\n3. Architecture:")
    print(f"   Components: {len(result['architecture_outline']['components'])} components")
    print(f"   Tech Stack: {result['architecture_outline']['tech_stack']}")

    print("\n4. UML Diagram:")
    uml = result['uml_diagram']
    if uml:
        lines = uml.strip().split('\n')
        print(f"   Generated {len(lines)} lines of PlantUML")
        print("   Preview:")
        for line in lines[:5]:
            print(f"   {line}")
        if len(lines) > 5:
            print("   ...")
    else:
        print("   (No UML diagram generated)")

    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)

    # Save full output
    with open("test_output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("\nFull output saved to: test_output.json")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
