from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from llm.wrapper import ask  # M5's wrapper for direct calls if needed
from agents.agent_a.requirements_analyst import RequirementsAnalyst

load_dotenv()
os.environ["OPENAI_API_KEY"] = "sk-fake-key-not-used"

# ── LLM for placeholder agents B and C (Week 4 will swap in M3/M4 real agents) ──
qwen_llm = LLM(
    model="qwen-max",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

agent_b = Agent(
    role="Software Developer",
    goal="Write clean, working Python code based on the JSON design plan provided by the analyst",
    backstory="You are an experienced Python developer who reads a structured design plan and writes production-ready code.",
    verbose=True,
    llm=qwen_llm
)

agent_c = Agent(
    role="QA Engineer",
    goal="Write pytest tests for the provided code, run analysis, and return a verified test report",
    backstory="You are a meticulous QA engineer who receives code from a developer and produces a full test report.",
    verbose=True,
    llm=qwen_llm
)


def run_pipeline(user_input: str) -> str:
    """Run the full A -> B -> C pipeline for a given user requirement.

    Stage 1 uses M2's real RequirementsAnalyst and saves analysis_output.json.
    Stages 2-3 use placeholder CrewAI agents until M3/M4 are wired in (Week 4).
    """
    # ── Stage 1: M2's real Agent A ──
    print("\n===== STAGE 1: AGENT A (Requirements Analysis) =====")
    analyst = RequirementsAnalyst()
    analysis = analyst.analyze(user_input)

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/analysis_output.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=4, ensure_ascii=False)
    print("Agent A output saved -> outputs/analysis_output.json")

    analysis_summary = json.dumps(analysis, ensure_ascii=False, indent=2)

    # ── Stage 2: Placeholder Agent B (inject real analysis as context) ──
    task_b = Task(
        description=f"""You are given a structured design plan from the Requirements Analyst.

        Here is the analysis output (PRD, user stories, architecture):
        {analysis_summary}

        Read it carefully and write complete, working Python code that implements it.
        Your response must include:
        - The full Python code
        - The filename to save it as
        - Any pip dependencies needed""",
        expected_output="Complete working Python code with filename and dependencies listed",
        agent=agent_b,
    )

    # ── Stage 3: Placeholder Agent C ──
    task_c = Task(
        description="""You are given Python code written by a developer.
        Your job is to:
        1. Review the code for bugs
        2. Write pytest test cases for it
        3. Identify any issues and suggest fixes
        4. Provide a final verdict: PASS or FAIL

        The code is provided in the context above.""",
        expected_output="A test report with: test cases, bug analysis, fixes applied, and final PASS/FAIL verdict",
        agent=agent_c,
        context=[task_b],
    )

    crew = Crew(
        agents=[agent_b, agent_c],
        tasks=[task_b, task_c],
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)


if __name__ == "__main__":
    # ... өмнөх код ...
    user_input = input("Enter your software requirement: ")
    result = run_pipeline(user_input)
    print("\n===== FINAL OUTPUT =====")
    print(result) # <--- Зөвхөн энэ мөрийг үлдээгээрэй

class crew:
    def __init__(self, crew):
        # M1-ийн өөрсдийнх нь үүсгэсэн crew объектыг энд холбоно
        self.crew = crew

    def run(self, user_input):
        # Чиний скриптээс ирэх prompt-ийг AI руу илгээнэ
        result = self.crew.kickoff(inputs={"user_input": user_input})
        return str(result)
  
