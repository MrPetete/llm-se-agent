# Agent A: Requirements Analyst

**Week 4 Update**: Added UML diagram generation and PRD validation

## Quick Start

```python
from requirements_analyst import RequirementsAnalyst

# Initialize
analyst = RequirementsAnalyst()

# Analyze requirements
user_input = """
I want to build a task management app where users can create tasks,
set deadlines, assign them to team members, and track progress.
"""

result = analyst.analyze(user_input)

# Access outputs
print("PRD:", result["prd"])
print("User Stories:", result["user_stories"])
print("Architecture:", result["architecture_outline"])
print("UML Diagram:", result["uml_diagram"])
```

## Files

| File | Description |
|------|-------------|
| `requirements_analyst.py` | Main CrewAI agent implementation |
| `prompts.py` | Prompt templates with few-shot examples |

## Output Schema

Agent A outputs JSON conforming to M1's shared data contract:

```json
{
  "prd": {
    "product_overview": "...",
    "target_users": ["..."],
    "core_features": [{"id": "F1", "name": "...", "description": "..."}],
    "functional_requirements": [{"id": "FR1", "requirement": "..."}],
    "non_functional_requirements": [{"category": "...", "requirement": "..."}],
    "success_metrics": [{"metric": "...", "target": "..."}],
    "validation_passed": true,
    "validation_notes": "..."
  },
  "user_stories": [
    {"feature_id": "F1", "story": "As a...", "acceptance_criteria": [...], "priority": "Must-have"}
  ],
  "architecture_outline": {
    "components": [...],
    "data_flow": [...],
    "tech_stack": {...},
    "architectural_decisions": [...]
  },
  "uml_diagram": "@startuml\n...\n@enduml"
}
```

## Features (Week 4)

| Feature | Description |
|---------|-------------|
| PRD Generation | Transforms raw requirements into structured PRD |
| Validation | Automatically validates PRD for testability and scope |
| User Stories | Generates user stories with acceptance criteria |
| Architecture Outline | System components, tech stack, data flow |
| UML Diagram | PlantUML component diagram for visualization |

## M2 Role Reference

This module fulfills **Member 2 (Agent A: Requirements Analyst)** from the team roadmap:

| Week | Status | Deliverable |
|------|--------|-------------|
| Week 1 | ✅ Done | Environment setup, CrewAI learning, initial prompt experiments |
| Week 2 | ✅ Done | Agent A prototype - PRD generation from raw requirements |
| Week 3 | ✅ Done | Prompt refinement with few-shot examples, test scenarios |
| Week 4 | ✅ Done | UML diagram generation, PRD validation, output polish |
| Week 5 | Pending | Integration with M1's orchestrator |
| Week 6 | Pending | Documentation and technical report |
