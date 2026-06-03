import time
import json
import os
import sys
from memory_profiler import memory_usage
from pylint import lint
from io import StringIO
from dotenv import load_dotenv  

from orchestrator.main import run_pipeline

load_dotenv()

class AdvancedTestHarness:
    """
    Advanced Test Harness (Complete 8-Scenario Version)
    Evaluates LLM-generated code across 8 specific test cases.
    """

    def __init__(self):
        self.results = []
        # All 8 scenarios based on the QA Lead's strategy
        self.scenarios = [
            {"id": "TC-01", "name": "Greeting App", "prompt": "Write a Python script that takes a user's name as input, greets them, and displays the current time."},
            {"id": "TC-02", "name": "Basic Calculator", "prompt": "Write a function that takes two numbers and an operator (+, -, *, /) and returns the result. Handle division by zero."},
            {"id": "TC-03", "name": "CSV Data Summary", "prompt": "Read a 'data.csv' file and print the average and sum of each numerical column using pandas."},
            {"id": "TC-04", "name": "To-Do List (DB)", "prompt": "Create a CLI application using SQLite to add, view, and delete tasks in a to-do list."},
            {"id": "TC-05", "name": "Web Scraper", "prompt": "Scrape all H1-H3 headers and links from a given URL and save them to a text file using BeautifulSoup."},
            {"id": "TC-06", "name": "Weather API", "prompt": "Use the requests library to fetch weather data for a specific city from an API and display the temperature and humidity."},
            {"id": "TC-07", "name": "FastAPI CRUD", "prompt": "Develop a simple Book Store REST API with at least 3 endpoints using FastAPI."},
            {"id": "TC-08", "name": "Multi-module Project", "prompt": "Create a project with two files: one for mathematical utility functions and another for logging the results."}
        ]

    def get_pylint_score(self, file_path):
        """Calculates PEP 8 compliance score out of 10."""
        pylint_output = StringIO()
        results = lint.Run([file_path], reporter=None, do_exit=False)
        score = results.linter.stats.global_note if hasattr(results.linter.stats, 'global_note') else 0
        return round(score, 2)

    def count_loc(self, code):
        """Counts effective Lines of Code (LOC)."""
        lines = [line for line in code.splitlines() if line.strip() and not line.strip().startswith('#')]
        return len(lines)

    def run_benchmark(self):
        print(f"🚀 Starting Full QA Benchmark (8 Scenarios)\n")
        
        for case in self.scenarios:
            print(f"[{case['id']}] Testing: {case['name']}...")
            
            start_time = time.time()
            # 1. Get output from the pipeline
            output_response = run_pipeline(case['prompt'])
            duration = round(time.time() - start_time, 2)
            
            # 2. ЭНЭ ХЭСГИЙГ ХУУЛЖ ТАВИНА (JSON-оос кодыг салгах)
            try:
                data = json.loads(output_response)
                output_code = data.get("code", "") 
            except:
                output_code = output_response
            
            # 3. Салгаж авсан цэвэр кодоо файлд бичнэ
            file_name = f"exec_{case['id']}.py"
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(output_code)
            
            # Measure metrics
            loc = self.count_loc(output_code)
            pylint_score = self.get_pylint_score(file_name)
            
            # Measure Peak Memory
            try:
                mem_usage_list = memory_usage((time.sleep, (0.5,)), interval=0.1)
                peak_mem = round(max(mem_usage_list) - min(mem_usage_list), 2)
            except Exception:
                peak_mem = 0

            result = {
                "id": case['id'],
                "name": case['name'],
                "duration_sec": duration,
                "lines_of_code": loc,
                "pylint_score": pylint_score,
                "peak_memory_mb": peak_mem,
                "status": "Success"
            }
            self.results.append(result)
            print(f"📊 {case['id']} Finished: {loc} LOC | ⭐ {pylint_score}/10 | {peak_mem} MB\n")
            
            if os.path.exists(file_name):
                os.remove(file_name)

        self.save_report()

    def save_report(self):
        with open("qa_metrics_report.json", "w") as f:
            json.dump(self.results, f, indent=4)
        print("💾 Full 8-scenario report saved to 'qa_metrics_report.json'.")

if __name__ == "__main__":
    harness = AdvancedTestHarness()
    harness.run_benchmark()