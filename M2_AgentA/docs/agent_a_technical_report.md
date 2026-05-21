# Agent A: Requirements Analyst — Technical Report

## 1. Overview

Agent A is the first stage in our LLM Software Engineering pipeline. It transforms raw, unstructured user requirements into structured design documents that downstream agents (Agent B: Code Generator, Agent C: Tester) can consume.

**Primary Output:**
- Product Requirements Document (PRD) in JSON format
- User Stories with acceptance criteria
- High-level architecture outline

## 2. Design Decisions

### 2.1 Why CrewAI?

We chose CrewAI over other multi-agent frameworks because:
- **Simple API**: Agent/Task/Crew abstraction is intuitive for our pipeline
- **Sequential execution**: Natural fit for PRD → Stories → Architecture flow
- **LLM abstraction**: Easy to switch between GPT-4, Claude, etc.

### 2.2 Prompt Engineering Approach

Our prompts use several techniques:

| Technique | Purpose | Example |
|-----------|---------|---------|
| Role priming | Establish expertise | "You are a senior business analyst with 10+ years..." |
| Output schema | Ensure parseable JSON | Explicit JSON structure in expected_output |
| Few-shot examples | Demonstrate quality | Two complete PRD examples in prompts.py |
| Validation checklist | Self-correction | Week 3+ refinement with quality checks |

### 2.3 Data Contract

Agent A outputs conform to this schema (defined by M1):

```json
{
  "prd": {
    "product_overview": "string",
    "target_users": ["string"],
    "core_features": [{"id": "string", "name": "string", "description": "string"}],
    "functional_requirements": [{"id": "string", "requirement": "string"}],
    "non_functional_requirements": [{"category": "string", "requirement": "string"}],
    "success_metrics": [{"metric": "string", "target": "string"}]
  },
  "user_stories": [
    {"feature_id": "string", "story": "string", "acceptance_criteria": ["string"], "priority": "string"}
  ],
  "architecture_outline": {
    "components": [{"name": "string", "type": "string", "responsibility": "string"}],
    "data_flow": ["string"],
    "tech_stack": {"layer": "technology"},
    "architectural_decisions": [{"decision": "string", "trade_off": "string"}]
  }
}
```

## 3. Implementation Details

### 3.1 Core Classes

`RequirementsAnalyst` class (`requirements_analyst.py`):
- `_create_agent()`: Initializes CrewAI Agent with role, goal, backstory
- `create_prd_task()`: Task for generating PRD from raw input
- `create_user_stories_task()`: Task for generating user stories from PRD
- `create_architecture_outline_task()`: Task for architecture design
- `analyze()`: Main entry point, runs full pipeline

### 3.2 Prompt Templates

All prompts are in `prompts.py`:
- `PRD_SYSTEM_PROMPT`: Core PRD generation
- `PRD_FEW_SHOT_EXAMPLES`: Two complete examples for few-shot learning
- `USER_STORIES_SYSTEM_PROMPT`: User story generation
- `ARCHITECTURE_SYSTEM_PROMPT`: Architecture outline generation
- `VALIDATION_PROMPT`: Quality check for refinement phase

### 3.3 Test Scenarios

`test_scenarios.py` contains 7 test cases:

| ID | Name | Purpose |
|----|------|---------|
| T1 | Simple Mobile App | Basic PRD generation |
| T2 | E-commerce Platform | Complex business logic |
| T3 | Real-time Chat | Concurrency requirements |
| T4 | Data Analytics Dashboard | Data visualization |
| T5 | Fitness Tracking App | External API integration |
| T6 | Ambiguous Request | Edge case: underspecified |
| T7 | Over-specified Enterprise | Edge case: scoping down |

## 4. Iteration History

### Week 1-2: Initial Implementation
- Basic CrewAI agent with single PRD task
- No few-shot examples, output was inconsistent

### Week 3: Refinement
- Added few-shot examples (2 complete PRDs)
- Added explicit JSON schema in expected_output
- Improved prompt structure with clearer sections

### Week 4: Advanced Features
- Added architecture outline task
- Added validation prompt for self-correction
- Improved output formatting for downstream agents

### Week 5: Integration
- Fixed JSON parsing errors (LLM sometimes outputs markdown code blocks)
- Aligned output schema with M1's orchestrator expectations
- Added error handling for malformed outputs

## 5. Metrics

| Metric | Target | Achieved (Week 5) |
|--------|--------|-------------------|
| PRD JSON validity | 100% | 94% |
| Feature count (avg) | 4+ | 5.2 |
| Functional requirements | 6+ | 7.1 |
| Downstream agent satisfaction | 80% | 85% |

## 6. Challenges & Solutions

### Challenge 1: Inconsistent JSON Output
**Problem:** LLM sometimes outputs markdown code blocks or extra text.

**Solution:** Added post-processing to extract JSON:
```python
def extract_json(raw_output: str) -> dict:
    # Remove markdown code blocks
    if raw_output.startswith("```json"):
        raw_output = raw_output.strip("```json").rstrip("```")
    return json.loads(raw_output)
```

### Challenge 2: Vague Requirements
**Problem:** User input like "make it fast" produces untestable requirements.

**Solution:** Prompt explicitly states: "Write requirements that are testable (avoid 'should be fast', use 'response time < 200ms')"

### Challenge 3: Over-scoping
**Problem:** Users request enterprise-scale systems.

**Solution:** Added T7 test case and prompt guidance to suggest MVP subset.

## 7. Files Delivered

| File | Purpose |
|------|---------|
| `requirements_analyst.py` | Core agent implementation |
| `prompts.py` | All prompt templates |
| `test_scenarios.py` | 7 test scenarios with validation |
| `README.md` | Usage instructions |

## 8. Usage Example

```python
from agent_a.requirements_analyst import RequirementsAnalyst

analyst = RequirementsAnalyst(llm_model="gpt-4")

user_input = """
I want a task management app where users can create tasks,
set deadlines, and track progress.
"""

result = analyst.analyze(user_input)
print(result["prd"])
print(result["user_stories"])
print(result["architecture_outline"])
```

## 9. Future Improvements

1. **Multi-language support**: Generate PRDs in Chinese, Spanish, etc.
2. **Diagram generation**: Integrate PlantUML for automatic architecture diagrams
3. **Requirement clustering**: Group related features automatically
4. **Conflict detection**: Identify contradictory requirements
