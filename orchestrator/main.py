from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
import os

load_dotenv()
os.environ["OPENAI_API_KEY"] = "sk-fake-key-not-used"

# Set up Qwen as the LLM
qwen_llm = LLM(
    model="qwen-max",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# ── Placeholder Agents (M2, M3, M4 will replace these) ──
agent_a = Agent(
    role="Requirements Analyst",
    goal="Analyze software requirements and produce a structured design plan",
    backstory="You are a senior software analyst who breaks down requirements clearly.",
    verbose=True,
    llm=qwen_llm
)

agent_b = Agent(
    role="Software Developer",
    goal="Write clean, working Python code based on a given design plan",
    backstory="You are an experienced Python developer who writes production-ready code.",
    verbose=True,
    llm=qwen_llm
)

agent_c = Agent(
    role="QA Engineer",
    goal="Test and debug the code, return a fixed and verified version",
    backstory="You are a meticulous QA engineer who catches bugs and fixes them.",
    verbose=True,
    llm=qwen_llm
)

# ── Placeholder Tasks ──
task_a = Task(
    description="Analyze this requirement: {user_input}",
    expected_output="A structured design plan in JSON format",
    agent=agent_a
)

task_b = Task(
    description="Based on the design plan, write the implementation code",
    expected_output="Working Python code",
    agent=agent_b
)

task_c = Task(
    description="Test and debug the code provided",
    expected_output="Debugged and verified code with a test report",
    agent=agent_c
)

# ── The Crew (Orchestrator glue) ──
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
