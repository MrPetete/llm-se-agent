"""
Agent A: Requirements Analyst
=============================
Takes raw user requirements and produces structured design documents:
- PRD (Product Requirements Document)
- User Stories with acceptance criteria
- High-level architecture outline

Built with CrewAI for the LLM Software Engineering Agent project.
"""

from crewai import Agent, Task, Crew, LLM
from typing import Dict, Any
import json
import os


class RequirementsAnalyst:
    """
    Agent A - Requirements Analyst

    Purpose: Transform raw user input into structured design documents
    that Agent B (Code Generator) can consume.
    """

    def __init__(self, llm_model=None):
        self.llm_model = llm_model
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """Create the Requirements Analyst CrewAI agent."""
        return Agent(
            role="Senior Requirements Analyst",
            goal="Transform raw user requirements into clear, structured PRDs and user stories",
            backstory="""You are a senior business analyst with 10+ years of experience
            in software requirements engineering. You excel at extracting clear, actionable
            requirements from ambiguous user descriptions. Your outputs are precise enough
            that developers can immediately start coding without clarification.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm_model or LLM(
                model="qwen-max",
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
        )

    def create_prd_task(self, requirements_text: str) -> Task:
        """Create the PRD generation task."""
        return Task(
            description=f"""
            Analyze the following user requirements and produce a complete PRD:

            USER INPUT:
            "{requirements_text}"

            Output a structured PRD with these sections:
            1. Product Overview (2-3 sentences)
            2. Target Users (bullet points)
            3. Core Features (numbered list with 1-sentence descriptions)
            4. Functional Requirements (numbered, testable statements)
            5. Non-Functional Requirements (performance, security, usability)
            6. Success Metrics (how we know this is working)

            Format: JSON with keys matching the schema below.
            """,
            expected_output="""
            {
                "product_overview": str,
                "target_users": list[str],
                "core_features": [{"id": str, "name": str, "description": str}],
                "functional_requirements": [{"id": str, "requirement": str}],
                "non_functional_requirements": [{"category": str, "requirement": str}],
                "success_metrics": [{"metric": str, "target": str}]
            }
            """,
            agent=self.agent,
        )

    def create_user_stories_task(self, prd_json: Dict[str, Any]) -> Task:
        """Create user stories from the PRD."""
        return Task(
            description=f"""
            Based on this PRD, generate detailed user stories with acceptance criteria:

            PRD: {json.dumps(prd_json, indent=2)}

            For each core feature, create:
            - User Story (As a [user], I want [goal], so that [benefit])
            - Acceptance Criteria (Given-When-Then format, 3-5 per story)
            - Priority (Must-have / Should-have / Could-have)

            Output as JSON array.
            """,
            expected_output="""
            [
                {
                    "feature_id": str,
                    "story": "As a ..., I want ..., so that ...",
                    "acceptance_criteria": ["Given ... When ... Then ..."],
                    "priority": "Must-have" | "Should-have" | "Could-have"
                }
            ]
            """,
            agent=self.agent,
        )

    def create_architecture_outline_task(self, prd_json: Dict[str, Any]) -> Task:
        """Create a high-level architecture outline."""
        return Task(
            description=f"""
            Based on this PRD, outline the system architecture:

            PRD: {json.dumps(prd_json, indent=2)}

            Include:
            - System components (backend, frontend, database, external services)
            - Data flow between components
            - Recommended tech stack (with brief justification)
            - Key architectural decisions and trade-offs
            - A PlantUML component diagram showing the architecture

            Output as structured text with sections.
            """,
            expected_output="""
            {
                "components": [{"name": str, "type": str, "responsibility": str}],
                "data_flow": [str],
                "tech_stack": {"layer": "technology", "justification": str},
                "architectural_decisions": [{"decision": str, "trade_off": str}],
                "uml_diagram": "PlantUML component diagram as a string"
            }
            """,
            agent=self.agent,
        )

    def create_uml_diagram_task(self, prd_json: Dict[str, Any], architecture_json: Dict[str, Any]) -> Task:
        """Create a PlantUML component diagram from the architecture."""
        return Task(
            description=f"""
            Based on this architecture, create a PlantUML component diagram:

            PRD Summary: {prd_json.get("product_overview", "")}
            Components: {json.dumps(architecture_json.get("components", []), indent=2)}
            Data Flow: {json.dumps(architecture_json.get("data_flow", []), indent=2)}

            Generate a PlantUML script that:
            - Shows all system components
            - Illustrates data flow between components
            - Uses proper PlantUML syntax (@startuml / @enduml)
            - Is renderable by any PlantUML renderer

            Output the raw PlantUML script as a string.
            """,
            expected_output="""
            {
                "plantuml_script": "@startuml\n...\n@enduml"
            }
            """,
            agent=self.agent,
        )

    def create_validated_prd_task(self, prd_json: Dict[str, Any]) -> Task:
        """Validate and refine the PRD for quality."""
        return Task(
            description=f"""
            Review and validate this PRD for quality:

            PRD: {json.dumps(prd_json, indent=2)}

            Validation Checklist:
            [ ] All requirements are testable (no vague terms like "fast", "user-friendly")
            [ ] Each feature has a clear, independent purpose
            [ ] Success metrics are quantifiable
            [ ] No contradictions between requirements
            [ ] Scope is appropriate for a student project

            If any item fails, revise the PRD section.
            Output the validated PRD with the same schema.
            """,
            expected_output="""
            {
                "product_overview": str,
                "target_users": list[str],
                "core_features": [{"id": str, "name": str, "description": str}],
                "functional_requirements": [{"id": str, "requirement": str}],
                "non_functional_requirements": [{"category": str, "requirement": str}],
                "success_metrics": [{"metric": str, "target": str}],
                "validation_passed": bool,
                "validation_notes": str
            }
            """,
            agent=self.agent,
        )

    def analyze(self, requirements_text: str) -> Dict[str, Any]:
        """
        Main entry point - run full requirements analysis.

        Args:
            requirements_text: Raw user input describing what they want to build

        Returns:
            Complete analysis with PRD, user stories, architecture outline, and UML diagram
        """
        # Create tasks
        prd_task = self.create_prd_task(requirements_text)

        # Run crew for PRD first
        crew = Crew(
            agents=[self.agent],
            tasks=[prd_task],
            verbose=True,
        )
        prd_result = crew.kickoff()
        prd_json = json.loads(prd_result)

        # Validate PRD
        validated_prd_task = self.create_validated_prd_task(prd_json)
        crew1b = Crew(agents=[self.agent], tasks=[validated_prd_task], verbose=True)
        validated_prd_result = crew1b.kickoff()
        validated_prd_json = json.loads(validated_prd_result)

        # Create and run user stories task
        stories_task = self.create_user_stories_task(validated_prd_json)
        crew2 = Crew(agents=[self.agent], tasks=[stories_task], verbose=True)
        stories_result = crew2.kickoff()

        # Create and run architecture outline task
        arch_task = self.create_architecture_outline_task(validated_prd_json)
        crew3 = Crew(agents=[self.agent], tasks=[arch_task], verbose=True)
        arch_result = crew3.kickoff()
        arch_json = json.loads(arch_result)

        # Create and run UML diagram task
        uml_task = self.create_uml_diagram_task(validated_prd_json, arch_json)
        crew4 = Crew(agents=[self.agent], tasks=[uml_task], verbose=True)
        uml_result = crew4.kickoff()
        uml_json = json.loads(uml_result)

        return {
            "prd": validated_prd_json,
            "user_stories": json.loads(stories_result),
            "architecture_outline": arch_json,
            "uml_diagram": uml_json.get("plantuml_script", ""),
        }


# Example usage
if __name__ == "__main__":
    analyst = RequirementsAnalyst(llm_model="qwen-max")

    sample_input = """
    I want to build a task management app where users can create tasks,
    set deadlines, assign them to team members, and track progress.
    It should send reminders and have a dashboard showing completion stats.
    """

    result = analyst.analyze(sample_input)
    print(json.dumps(result, indent=2))
