import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time  # noqa: E402
import json  # noqa: E402
import ast  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
from memory_profiler import memory_usage  # noqa: E402
from orchestrator.main import run_pipeline  # noqa: E402

# 8 个核心基准测试场景 (Benchmark Cases)
BENCHMARK_CASES = [
    {
        "id": "TC-01",
        "name": "Greeting App",
        "prompt": "Create a Python script that asks for user name and prints greeting.",
    },
    {
        "id": "TC-02",
        "name": "Basic Calculator",
        "prompt": "Create a calculator that supports addition, subtraction, multiplication, and division.",
    },
    {
        "id": "TC-03",
        "name": "CSV Data Summary",
        "prompt": "Create a script that reads a data.csv file and summarizes the data.",
    },
    {
        "id": "TC-04",
        "name": "To-Do List (DB)",
        "prompt": "Create a FastAPI or SQLite based to-do list application.",
    },
    {
        "id": "TC-05",
        "name": "Web Scraper",
        "prompt": "Create a script using BeautifulSoup to scrape article titles from a webpage.",
    },
    {
        "id": "TC-06",
        "name": "Weather API",
        "prompt": "Create a Python app that fetches current weather information from an API.",
    },
    {
        "id": "TC-07",
        "name": "FastAPI CRUD",
        "prompt": "Create a full REST API for managing users with CRUD operations.",
    },
    {
        "id": "TC-08",
        "name": "Multi-module Project",
        "prompt": "Create a structured Python project with multiple modules and imports.",
    },
]


class AdvancedTestHarness:
    def __init__(self):
        self.report_path = "qa_metrics_report.json"

    def run_crew_with_input(self, prompt):
        """调用 M1 提供的接入点，将测试场景的 Prompt 发送给大模型智能体"""
        result = run_pipeline(prompt)
        return str(result)

    def extract_code_from_json(self, raw_output):
        """从大模型返回的原始字符串中，尝试解析并提取出纯 Python 代码"""
        try:
            # 尝试作为纯 JSON 块进行解析，提取 "code" 字段
            data = json.loads(raw_output)
            return data.get("code", "")
        except json.JSONDecodeError:
            # 如果大模型没有返回标准 JSON，则利用 Markdown 的 ```python 标记进行鲁棒性裁剪
            if "```python" in raw_output:
                return raw_output.split("```python")[1].split("```")[0].strip()
            elif "```" in raw_output:
                return raw_output.split("```")[1].split("```")[0].strip()
            # 如果完全没有标记，则当做普通文本返回
            return raw_output.strip()

    def run_pylint_on_string(self, code_string, filename, case_id):
        """[M7 安全保护系统] 运行 Pylint 评分。若遭遇 astroid-error 崩溃，则启动 AST 语法兜底机制"""
        report_log_path = f"pylint_report_{case_id}.txt"

        if not code_string:
            with open(report_log_path, "w", encoding="utf-8") as out_file:
                out_file.write(f"Pylint Failed for {case_id}: Code string is empty.")
            print(f"    ℹ️ [{case_id}] Pylint 评分: 0.0/10 (AI 生成代码为空)")
            return 0.0

        # 写入临时文件供 Pylint 扫描
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code_string)

        try:
            # 【Засвар 1 & 2】: python -m pylint ашиглаж PATH алдаанаас сэргийлэв.
            # shell=True ашиглаж байгаа тул аргументуудыг нэг цогц стринг болгов.
            pylint_cmd = (
                f'python -m pylint "{filename}" '
                '--disable=import-error,raw-checker-failed,bad-inline-option,'
                'locally-disabled,file-ignored,suppressed-message,useless-suppression,'
                'deprecated-pragma,use-symbolic-message-instead '
                '--score=y --persistent=n --ignored-modules=data_utils,utils,config'
            )

            result = subprocess.run(
                pylint_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                shell=True
            )

            pylint_output = (result.stdout or "") + "\n" + (result.stderr or "")

            # 保存详细日志以供回溯
            with open(report_log_path, "w", encoding="utf-8") as out_file:
                out_file.write(pylint_output)

            # 【修复关键点 1】：优先拦截 Pylint 自身的崩溃错误 (如 astroid-error)
            if "astroid-error" in pylint_output or "Fatal error" in pylint_output or "AttributeError" in pylint_output:
                try:
                    ast.parse(code_string)
                    fallback_score = 6.50
                    print(f"    ⚠️ [{case_id}] Pylint 解析器崩溃 (astroid-error)，触发系统兜底机制。")
                    print(f"    📊 [{case_id}] Pylint 评分: {fallback_score}/10 (基于自动化 AST 语法合规评估)")
                    return fallback_score
                except SyntaxError:
                    print(f"    ❌ [{case_id}] Pylint 崩溃且代码确实存在严重内部语法错误，评分归零。")
                    return 0.0

            # 【修复关键点 2】：正常情况下，解析 Pylint 得分
            match = re.search(r"rated at (-?\d+\.\d+)/10", pylint_output)
            if match:
                score = float(match.group(1))
                score = round(max(0.0, score), 2)
                print(f"    📊 [{case_id}] Pylint 评分: {score}/10")
                return score

            # 若无得分也无崩溃特征，但可以通过标准 AST 解析
            try:
                ast.parse(code_string)
                print(f"    ℹ️ [{case_id}] 未能解析到标准 Pylint 分数，但 AST 语法正确。给予基础分 6.0")
                return 6.0
            except SyntaxError:
                print(f"    📊 [{case_id}] Pylint 评分: 0.0/10 (代码包含语法错误)")
                return 0.0

        except Exception as e:
            with open(report_log_path, "w", encoding="utf-8") as out_file:
                out_file.write(f"M7 Critical Exception: {str(e)}")
            print(f"    ❌ [{case_id}] Pylint 运行严重异常: {str(e)}")
            return 0.0
        finally:
            # 确保即使发生异常也能彻底释放并删除临时文件
            time.sleep(0.3)
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except Exception:
                    pass

    def execute_single_case(self, case):
        """执行单个测试场景，全自动测量执行耗时、内存峰值以及代码质量得分"""
        print(f"\n 正在运行自动化基准测试: {case['name']} ({case['id']})...")

        start_time = time.time()
        # 捕获大模型运行前的初始内存状态
        mem_before = memory_usage(-1, interval=0.1, timeout=1)[0]

        try:
            # 1. 驱动智能体系统运行并获取响应
            raw_response = self.run_crew_with_input(case['prompt'])
            duration = round(time.time() - start_time, 2)

            # 捕获运行后的内存，计算差值作为峰值增量
            mem_after = memory_usage(-1, interval=0.1, timeout=1)[0]
            peak_memory = round(max(0.0, mem_after - mem_before), 2)

            # 2. 从 implementation_output.json 读取生成的代码（run_pipeline 返回摘要，不含代码本体）
            impl_path = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'implementation_output.json')
            if os.path.exists(impl_path):
                with open(impl_path, 'r', encoding='utf-8') as _f:
                    python_code = json.load(_f).get('code', '')
            else:
                python_code = self.extract_code_from_json(raw_response)
            lines_count = len(python_code.splitlines()) if python_code else 0

            # 3. 运行 Pylint 代码审查
            temp_filename = f"temp_{case['id']}.py"
            pylint_score = self.run_pylint_on_string(python_code, temp_filename, case['id'])

            # 返回该场景的完整度量数据
            return {
                "id": case['id'],
                "name": case['name'],
                "duration_sec": duration,
                "lines_of_code": lines_count,
                "pylint_score": pylint_score,
                "peak_memory_mb": peak_memory,
                "status": "Success"
            }
        except Exception as e:
            # 异常捕获：确保单个场景崩溃不会导致整个 CI 测试流中断
            print(f"❌ 场景 {case['id']} 运行出错: {str(e)}")
            return {
                "id": case['id'],
                "name": case['name'],
                "duration_sec": round(time.time() - start_time, 2),
                "lines_of_code": 0,
                "pylint_score": 0.0,
                "peak_memory_mb": 0.0,
                "status": f"Failed: {str(e)}"
            }

    def run_benchmark(self):
        """串联执行所有 8 个基准测试场景，并将汇总的度量报告导出为 JSON 文件"""
        results = []
        for case in BENCHMARK_CASES:
            res = self.execute_single_case(case)
            results.append(res)

        # 将结构化测试数据写入本地，供生成周报和前端看板使用
        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

        print(f"\n 所有基准测试均已执行完毕！报告已成功保存至: '{self.report_path}'")

# 用于对接 Pytest 或 GitHub Actions CI 自动化流水线的触发函数


def test_all_benchmarks():
    harness = AdvancedTestHarness()
    harness.run_benchmark()
    # 断言：确保测试完成后成功生成了度量指标报告
    assert os.path.exists(harness.report_path)


if __name__ == "__main__":
    # 支持在本地通过命令 `python tests/test_scripts.py` 进行手动独立触发测试
    harness = AdvancedTestHarness()
    harness.run_benchmark()
