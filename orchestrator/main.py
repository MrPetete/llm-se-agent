from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
import os
import sys

# ── Use M5's wrapper config ──
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from llm.wrapper import ask  # M5's wrapper for direct calls if needed

load_dotenv()
os.environ["OPENAI_API_KEY"] = "sk-fake-key-not-used"

# ── LLM for CrewAI agents (uses same DashScope config as M5's wrapper) ──
qwen_llm = LLM(
    model="qwen-max",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# ── Agents ──
agent_a = Agent(
    role="Requirements Analyst",
    goal="Analyze software requirements and produce a structured JSON design plan",
    backstory="You are a senior software analyst who breaks down requirements clearly and always responds in valid JSON.",
    verbose=True,
    llm=qwen_llm
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

# ── Tasks ──
task_a = Task(
    description="""Analyze this software requirement: {user_input}

    You MUST respond with a valid JSON object following this exact structure:
    {{
        "requirement_summary": "short summary of what the user wants",
        "components": ["component1", "component2"],
        "design_plan": "step by step implementation plan",
        "dependencies": ["library1", "library2"]
    }}
    Respond with JSON only. No extra text.""",
    expected_output="A valid JSON object with keys: requirement_summary, components, design_plan, dependencies",
    agent=agent_a
)

task_b = Task(
    description="""You are given a structured design plan from the Requirements Analyst.
    Read it carefully and write complete, working Python code that implements it.

    The design plan is provided in the context above.

    Your response must include:
    - The full Python code
    - The filename to save it as
    - Any pip dependencies needed""",
    expected_output="Complete working Python code with filename and dependencies listed",
    agent=agent_b,
    context=[task_a]  # ← This is the key change: task_b receives task_a's output
)

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
    context=[task_a, task_b]  # ← task_c receives both previous outputs
)

# ── Crew ──
crew = Crew(
    agents=[agent_a, agent_b, agent_c],
    tasks=[task_a, task_b, task_c],
    verbose=True
)

# ── Entry point ──
if __name__ == "__main__":
    user_input = input("Enter your software requirement: ")
    result = crew.kickoff(inputs={"user_input": user_input})
    print("\n===== FINAL OUTPUT =====")
    
    print(result)

    print(result)
    
class SoftwareEngineeringCrew:
    def __init__(self):
        # М1-ийн өөрсдийнх нь үүсгэсэн crew объектыг энд холбоно
        self.crew = crew 

    def run(self, user_input):
        # Чиний скриптээс ирэх prompt-ийг AI руу илгээнэ
        result = self.crew.kickoff(inputs={"user_input": user_input})
        return str(result)
