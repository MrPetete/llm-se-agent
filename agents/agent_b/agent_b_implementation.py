import json
import os
import ast
import re

from dotenv import load_dotenv
import dashscope


def read_json_file(file_path):
    """
    Read Agent A JSON output.
    Agent A output must follow schemas/analysis_output.json.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_analysis_output(agent_a_data):
    """
    Validate Agent A output using the updated analysis_output.json schema.
    Agent A now provides PRD, user stories, and architecture outline.
    """
    required_fields = [
        "prd",
        "user_stories",
        "architecture_outline"
    ]

    missing_fields = []

    for field in required_fields:
        if field not in agent_a_data:
            missing_fields.append(field)

    if missing_fields:
        return False, f"Missing required fields: {missing_fields}"

    if not isinstance(agent_a_data["prd"], dict):
        return False, "prd must be an object"

    if not isinstance(agent_a_data["user_stories"], list):
        return False, "user_stories must be a list"

    if not isinstance(agent_a_data["architecture_outline"], dict):
        return False, "architecture_outline must be an object"

    return True, "Agent A output is valid"


def detect_project_topic(agent_a_data):
    """
    Detect the project topic from the updated Agent A PRD output.
    This helps Agent B choose the filename and class name.
    """
    prd = agent_a_data.get("prd", {})
    architecture = agent_a_data.get("architecture_outline", {})

    core_features = prd.get("core_features", [])
    functional_requirements = prd.get("functional_requirements", [])

    text_parts = [
        prd.get("product_overview", ""),
        architecture.get("data_flow", ""),
        " ".join(core_features) if isinstance(core_features, list) else str(core_features),
        " ".join(functional_requirements)
        if isinstance(functional_requirements, list)
        else str(functional_requirements)
    ]

    text = " ".join(text_parts).lower()

    if "product" in text:
        return "product", "ProductManager", "product_manager.py"

    if "student" in text:
        return "student", "StudentManager", "student_manager.py"

    if "library" in text or "book" in text:
        return "book", "LibraryManager", "library_manager.py"

    if "employee" in text:
        return "employee", "EmployeeManager", "employee_manager.py"

    if "login" in text or "user" in text or "password" in text:
        return "user", "UserManager", "user_manager.py"

    return "item", "ItemManager", "item_manager.py"


def mock_llm_generate_implementation(agent_a_data):
    """
    Mock LLM implementation generator.

    This simulates Agent B's LLM output.
    Later, this function can be replaced with Qwen / CrewAI API call.
    The output must follow schemas/implementation_output.json.
    """
    topic, class_name, filename = detect_project_topic(agent_a_data)

    if topic == "product":
        code = '''class ProductManager:
    def __init__(self):
        self.products = {}

    def add_product(self, product_id, name, price, stock):
        if product_id in self.products:
            return False, "Product already exists"

        self.products[product_id] = {
            "product_id": product_id,
            "name": name,
            "price": price,
            "stock": stock
        }
        return True, "Product added successfully"

    def delete_product(self, product_id):
        if product_id not in self.products:
            return False, "Product not found"

        del self.products[product_id]
        return True, "Product deleted successfully"

    def update_product(self, product_id, name=None, price=None, stock=None):
        if product_id not in self.products:
            return False, "Product not found"

        if name is not None:
            self.products[product_id]["name"] = name
        if price is not None:
            self.products[product_id]["price"] = price
        if stock is not None:
            self.products[product_id]["stock"] = stock

        return True, "Product updated successfully"

    def search_product(self, product_id):
        if product_id not in self.products:
            return None

        return self.products[product_id]

    def list_products(self):
        return list(self.products.values())


if __name__ == "__main__":
    manager = ProductManager()

    print("Add products:")
    print(manager.add_product("P001", "Laptop", 899.99, 10))
    print(manager.add_product("P002", "Mouse", 19.99, 50))

    print("\\nList products:")
    print(manager.list_products())

    print("\\nSearch product P001:")
    print(manager.search_product("P001"))

    print("\\nUpdate product P001:")
    print(manager.update_product("P001", price=799.99, stock=8))
    print(manager.search_product("P001"))

    print("\\nDelete product P002:")
    print(manager.delete_product("P002"))

    print("\\nFinal products:")
    print(manager.list_products())
'''
    elif topic == "student":
        code = '''class StudentManager:
    def __init__(self):
        self.students = {}

    def add_student(self, student_id, name, age, major):
        if student_id in self.students:
            return False, "Student already exists"

        self.students[student_id] = {
            "student_id": student_id,
            "name": name,
            "age": age,
            "major": major
        }
        return True, "Student added successfully"

    def delete_student(self, student_id):
        if student_id not in self.students:
            return False, "Student not found"

        del self.students[student_id]
        return True, "Student deleted successfully"

    def update_student(self, student_id, name=None, age=None, major=None):
        if student_id not in self.students:
            return False, "Student not found"

        if name is not None:
            self.students[student_id]["name"] = name
        if age is not None:
            self.students[student_id]["age"] = age
        if major is not None:
            self.students[student_id]["major"] = major

        return True, "Student updated successfully"

    def search_student(self, student_id):
        if student_id not in self.students:
            return None

        return self.students[student_id]

    def list_students(self):
        return list(self.students.values())


if __name__ == "__main__":
    manager = StudentManager()

    print("Add students:")
    print(manager.add_student("S001", "Alice", 20, "Computer Science"))
    print(manager.add_student("S002", "Bob", 21, "Software Engineering"))

    print("\\nList students:")
    print(manager.list_students())

    print("\\nSearch student S001:")
    print(manager.search_student("S001"))

    print("\\nUpdate student S001:")
    print(manager.update_student("S001", age=22))
    print(manager.search_student("S001"))

    print("\\nDelete student S002:")
    print(manager.delete_student("S002"))

    print("\\nFinal students:")
    print(manager.list_students())
'''
    else:
        code = f'''class {class_name}:
    def __init__(self):
        self.items = {{}}

    def add_item(self, item_id, name):
        if item_id in self.items:
            return False, "Item already exists"

        self.items[item_id] = {{
            "item_id": item_id,
            "name": name
        }}
        return True, "Item added successfully"

    def delete_item(self, item_id):
        if item_id not in self.items:
            return False, "Item not found"

        del self.items[item_id]
        return True, "Item deleted successfully"

    def search_item(self, item_id):
        return self.items.get(item_id)

    def list_items(self):
        return list(self.items.values())


if __name__ == "__main__":
    manager = {class_name}()

    print(manager.add_item("I001", "Sample Item"))
    print(manager.list_items())
'''

    implementation_output = {
        "code": code,
        "filename": filename,
        "language": "python",
        "dependencies": agent_a_data.get("dependencies", []),
        "notes": (
            "Generated by Agent B Code Generator. "
            "The implementation uses in-memory dictionary storage and includes a simple command-line demonstration. "
            "Agent C can generate pytest cases based on the CRUD methods in this file."
        )
    }

    return implementation_output


def validate_implementation_output(implementation_output):
    """
    Validate Agent B output using the required fields from implementation_output.json.
    """
    required_fields = [
        "code",
        "filename",
        "language",
        "dependencies"
    ]

    missing_fields = []

    for field in required_fields:
        if field not in implementation_output:
            missing_fields.append(field)

    if missing_fields:
        return False, f"Missing required fields: {missing_fields}"

    if not isinstance(implementation_output["code"], str):
        return False, "code must be a string"

    if not isinstance(implementation_output["filename"], str):
        return False, "filename must be a string"

    if not isinstance(implementation_output["language"], str):
        return False, "language must be a string"

    if not isinstance(implementation_output["dependencies"], list):
        return False, "dependencies must be a list"

    return True, "Agent B output is valid"


def check_python_syntax_from_code(code):
    """
    Check Python syntax from code string.
    """
    try:
        ast.parse(code)
        return True, "passed"
    except SyntaxError as error:
        return False, f"Syntax error: {error}"


def save_implementation_output(output_dir, implementation_output):
    """
    Save official Agent B JSON output and generated Python code file.
    """
    os.makedirs(output_dir, exist_ok=True)

    implementation_json_path = os.path.join(output_dir, "implementation_output.json")

    with open(implementation_json_path, "w", encoding="utf-8") as file:
        json.dump(implementation_output, file, indent=4, ensure_ascii=False)

    generated_project_dir = os.path.join(output_dir, "generated_project")
    os.makedirs(generated_project_dir, exist_ok=True)

    code_file_path = os.path.join(
        generated_project_dir,
        implementation_output["filename"]
    )

    with open(code_file_path, "w", encoding="utf-8") as file:
        file.write(implementation_output["code"])

    return implementation_json_path, code_file_path


def build_qwen_prompt(agent_a_data):
    """
    Build prompt for Qwen to generate Agent B implementation output.
    The input follows the updated Agent A analysis_output.json schema.
    """
    prd = agent_a_data.get("prd", {})
    user_stories = agent_a_data.get("user_stories", [])
    architecture = agent_a_data.get("architecture_outline", {})

    product_overview = prd.get("product_overview", "")
    core_features = prd.get("core_features", [])
    functional_requirements = prd.get("functional_requirements", [])
    data_flow = architecture.get("data_flow", "")

    agent_a_json = json.dumps(agent_a_data, indent=4, ensure_ascii=False)

    return f"""
You are Agent B: Code Generator in an LLM-based Software Engineering Agent
system.

Your input is Agent A analysis output following the updated schema:
- prd: object with product_overview, core_features, functional_requirements
- user_stories: array of user stories
- architecture_outline: object with architecture and data flow information

Your task is to generate Python implementation code based on the PRD and
architecture.

Important Agent A fields:

Product overview:
{product_overview}

Core features:
{core_features}

Functional requirements:
{functional_requirements}

Architecture data flow:
{data_flow}

User stories:
{user_stories}

You must return ONLY valid JSON.
Do not use markdown code blocks.
Do not add explanations outside JSON.

The JSON output must follow this schema:
{{
    "code": "actual Python code as a string",
    "filename": "suggested_file_name.py",
    "language": "python",
    "dependencies": [],
    "notes": "short notes for Agent C"
}}

Rules:
1. Generate clean and runnable Python code.
2. Use simple student-friendly code.
3. Do not use external libraries unless required.
4. Include a command-line demo under if __name__ == "__main__".
5. Make sure the code can pass ast.parse syntax checking.
6. The filename should match the project topic.
7. The code should implement the core features and requirements.

Full Agent A input:
{agent_a_json}
"""


def extract_json_from_text(text):
    """
    Extract JSON object from Qwen response text.
    """
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```json", "", text)
        text = re.sub(r"^```", "", text)
        text = re.sub(r"```$", "", text)
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON object found in Qwen response")

    return text[start:end + 1]
    
def get_qwen_content(response):
    """
    Get generated text from different DashScope/Qwen response formats.
    """
    output = response.get("output", {})

    text = output.get("text")
    if text:
        return text

    choices = output.get("choices")
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content")
        if content:
            return content

    raise ValueError(f"Cannot extract Qwen content from response: {output}")

def qwen_generate_implementation(agent_a_data):
    """
    Generate Agent B implementation output using Qwen / DashScope API.
    """
    load_dotenv()

    api_key = os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY is missing. Check your .env file.")

    dashscope.api_key = api_key
    dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

    prompt = build_qwen_prompt(agent_a_data)

    response = dashscope.Generation.call(
        model="qwen-turbo",
        prompt=prompt
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Qwen API call failed: {response.code} - {response.message}"
        )

    content = get_qwen_content(response)    

    json_text = extract_json_from_text(content)
    implementation_output = json.loads(json_text)

    return implementation_output


def build_repair_prompt(agent_a_data, implementation_output, error_message):
    """
    Build prompt for Qwen to repair invalid generated Python code.
    """
    agent_a_json = json.dumps(agent_a_data, indent=4, ensure_ascii=False)
    bad_output_json = json.dumps(
        implementation_output,
        indent=4,
        ensure_ascii=False
    )

    return f"""
You are Agent B: Code Generator.

The previous generated implementation has an error.

Agent A input:
{agent_a_json}

Previous Agent B output:
{bad_output_json}

Error message:
{error_message}

Please repair the implementation.

Return ONLY valid JSON.
Do not use markdown code blocks.
Do not add explanations outside JSON.

The JSON output must follow this schema:
{{
    "code": "fixed Python code as a string",
    "filename": "suggested_file_name.py",
    "language": "python",
    "dependencies": [],
    "notes": "short notes for Agent C"
}}

Rules:
1. Keep the same project requirement.
2. Fix the Python syntax problem.
3. The code must pass ast.parse.
4. Use simple runnable Python code.
"""


def qwen_repair_implementation(agent_a_data, implementation_output, error_message):
    """
    Ask Qwen to repair invalid Agent B implementation output.
    """
    load_dotenv()

    api_key = os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY is missing. Check your .env file.")

    dashscope.api_key = api_key
    dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

    prompt = build_repair_prompt(
        agent_a_data,
        implementation_output,
        error_message
    )

    response = dashscope.Generation.call(
        model="qwen-turbo",
        prompt=prompt
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Qwen repair failed: {response.code} - {response.message}"
        )

    content = get_qwen_content(response)

    json_text = extract_json_from_text(content)
    repaired_output = json.loads(json_text)

    return repaired_output


def run_agent_b(input_path, output_dir):
    """
    Main Agent B workflow.

    Input:
        Agent A output JSON following schemas/analysis_output.json

    Output:
        Agent B implementation JSON following schemas/implementation_output.json
    """
    agent_a_data = read_json_file(input_path)

    analysis_valid, analysis_message = validate_analysis_output(agent_a_data)

    if not analysis_valid:
        return {
            "success": False,
            "message": analysis_message,
            "stage": "validate_analysis_output"
        }

    retry_used = False
    retry_reason = "none"

    try:
        implementation_output = qwen_generate_implementation(agent_a_data)
        generation_mode = "qwen_api"
    except Exception as error:
        print(f"Qwen generation failed, fallback to mock mode: {error}")
        implementation_output = mock_llm_generate_implementation(agent_a_data)
        generation_mode = "mock_llm_fallback"
        retry_used = True
        retry_reason = "qwen_api_failed_fallback_to_mock"

    implementation_valid, implementation_message = validate_implementation_output(
        implementation_output
    )

    if not implementation_valid:
        return {
            "success": False,
            "message": implementation_message,
            "stage": "validate_implementation_output"
        }

    syntax_passed, syntax_message = check_python_syntax_from_code(
        implementation_output["code"]
    )

    if not syntax_passed and generation_mode == "qwen_api":
        try:
            implementation_output = qwen_repair_implementation(
                agent_a_data,
                implementation_output,
                syntax_message
            )

            retry_used = True
            retry_reason = "syntax_error_repaired_by_qwen"
            generation_mode = "qwen_api_retry"

            syntax_passed, syntax_message = check_python_syntax_from_code(
                implementation_output["code"]
            )
        except Exception as error:
            retry_used = True
            retry_reason = f"syntax_repair_failed: {error}"

    implementation_json_path, code_file_path = save_implementation_output(
        output_dir,
        implementation_output
    )

    result = {
        "success": syntax_passed,
        "message": "Agent B implementation generation finished",
        "input_schema": "schemas/analysis_output.json",
        "output_schema": "schemas/implementation_output.json",
        "implementation_json": implementation_json_path,
        "generated_code_file": code_file_path,
        "filename": implementation_output["filename"],
        "language": implementation_output["language"],
        "dependencies": implementation_output["dependencies"],
        "syntax_check": syntax_message,
        "mode": generation_mode,
        "retry_used": retry_used,
        "retry_reason": retry_reason
    }

    return result


if __name__ == "__main__":
    input_path = "tests/agent_b_sample_input.json"
    output_dir = "outputs"

    result = run_agent_b(input_path, output_dir)

    print(json.dumps(result, indent=4, ensure_ascii=False))
