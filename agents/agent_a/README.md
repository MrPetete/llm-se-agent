# Agent A: Requirements Analyst

## Quick Start

```python
from agent_a.requirements_analyst import RequirementsAnalyst

# Initialize
analyst = RequirementsAnalyst(llm_model="gpt-4")

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
    "success_metrics": [{"metric": "...", "target": "..."}]
  },
  "user_stories": [...],
  "architecture_outline": {...}
}
```

## M2 Role Reference

This module fulfills **Member 2 (Agent A: Requirements Analyst)** from the team roadmap:

- **Week 1-2**: Learn CrewAI, build initial PRD generator
- **Week 3**: Refine prompts with few-shot examples
- **Week 4**: Add architecture outline and validation
- **Week 5**: Integration with M1's orchestrator
- **Week 6**: Documentation and technical report

See the technical report in the docs folder for implementation details.
