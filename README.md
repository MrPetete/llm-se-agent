# llm-se-agent
LLM-Based Software Engineering Agent — CrewAI multi-agent system

一个 AI 驱动的开发助手，接收自然语言需求，自动完成需求分析、代码生成、测试编写和错误调试——全流程端到端。

---

## 项目简介

`llm-se-agent` 是基于 [CrewAI](https://github.com/joaomdmoura/crewAI) 构建、由通义千问（Qwen-Max，via DashScope）驱动的多智能体流水线。输入一句自然语言描述（如 *"创建一个登录系统"*），系统会按序调度三个专职 AI 智能体，自动生成经过测试和调试的完整代码，无需人工干预。

本项目为软件工程课程作业，由 7 人团队完成，旨在验证大语言模型自动化软件开发核心生命周期的可行性。

---

## 工作原理

```
用户输入（自然语言需求）
    │
    ▼
┌─────────────────────┐
│  Agent A            │  需求分析师
│  (M2)               │  → 生成 PRD、用户故事、架构概述
└────────┬────────────┘
         │  analysis_output.json
         ▼
┌─────────────────────┐
│  Agent B            │  代码生成器
│  (M3)               │  → 根据 PRD 生成实现代码
└────────┬────────────┘
         │  implementation_output.json
         ▼
┌─────────────────────┐
│  Agent C            │  测试与调试器
│  (M4)               │  → 编写 pytest 测试、在沙箱中执行、
└────────┬────────────┘    分类并修复失败用例
         │  test_output.json / debug_output.json
         ▼
    最终输出
```

所有智能体间通信均通过经过校验的 JSON Schema 进行。编排器（`M1`）负责管理流水线、执行数据合约、处理 CrewAI 任务排序。

## 快速开始

**1. 克隆仓库并检查环境**

```bash
git clone https://github.com/<your-org>/llm-se-agent.git
cd llm-se-agent
pip install -r requirements.txt
python scripts/doctor.py
```

**2. 配置 API 密钥**

```bash
cp .env.example .env
# 编辑 .env 文件，填写以下内容：
# LLM_PROVIDER=qwen
# DASHSCOPE_API_KEY=your_key_here
```

**3. 运行流水线**

```bash
python run.py build "创建一个待办事项的 REST API"
```

**4. 其他 CLI 命令**

```bash
python run.py doctor   # 重新运行环境检查
python run.py stats    # 查看 logs/ 中的 LLM 调用统计
```

**输出**保存在 `outputs/<时间戳>/` 目录下，包含 `analysis_output.json`、`implementation_output.json`、`test_output.json`、`debug_output.json` 及所有生成的代码文件。

---

## 智能体介绍

### Agent A — 需求分析师
基于 CrewAI 实现。接收自然语言 prompt，依次执行三个任务：PRD 生成、用户故事扩展、架构概述。采用少样本提示（2 个示例），输出结构化 JSON，经 `schemas/analysis_output.json` 校验。

### Agent B — 代码生成器
接收 Agent A 的结构化 PRD，通过 Qwen 生成可运行的 Python 实现代码。内置 `ast.parse` 语法校验，失败时进行一次 Qwen 修复尝试，并提供确定性模拟回退机制。通过 `retry_used` / `retry_reason` 字段将重试状态暴露给编排器。

### Agent C — 测试与调试器
读取 Agent B 的代码输出，通过 Qwen 生成 pytest 测试套件，并在子进程沙箱中执行。测试失败时，将回溯信息分类至 9 个类别（TypeError、ImportError、AttributeError、AssertionError 等），生成针对性修复方案并重新运行测试进行验证。输出 `debug_output.json`，包含修复前后的完整计数与已应用的修复内容。

---

## 团队成员

| 成员 | 角色 | 职责 |
|------|------|------|
| M1 | 组长 & 编排器 | 系统架构、JSON Schema、CrewAI 流水线、集成 |
| M2 | Agent A — 需求分析师 | PRD 生成、用户故事、架构概述 |
| M3 | Agent B — 代码生成器 | 代码生成、语法验证、修复循环 |
| M4 | Agent C — 测试与调试器 | 测试生成、沙箱执行、Bug 分类与修复 |
| M5 | DevOps & LLM 基础设施 | LLM 封装器、CI/CD、Docker、CLI、配置、doctor.py |
| M6 | 文档 & 集成支持 | 技术报告、集成参考文档、风格指南、使用指南 |
| M7 | QA & 评估 | 8 个测试场景（TC-01–TC-08）、KPI 指标、评估报告 |

---

## 测试场景

M7 设计了覆盖三个难度层级的 8 个评估场景：

| 编号 | 名称 | 难度 |
|------|------|------|
| TC-01 | 问候应用 | 简单 |
| TC-02 | 基础计算器 | 简单 |
| TC-03 | CSV 汇总工具 | 简单 |
| TC-04 | 带数据库的待办清单 | 中等 |
| TC-05 | 网页爬虫 | 中等 |
| TC-06 | 天气 API 客户端 | 中等 |
| TC-07 | FastAPI CRUD 接口 | 困难 |
| TC-08 | 多模块项目 | 中等 |

**每个场景追踪的 KPI：** 代码行数（LOC）、Pylint 评分（0–10）、执行时间、峰值内存占用、通过/失败正确性。

---

## 技术栈

- **LLM 框架：** [CrewAI](https://github.com/joaomdmoura/crewAI)
- **LLM 提供商：** 通义千问（Qwen-Max via [DashScope](https://dashscope.aliyun.com/)）（可插拔：支持 OpenAI / Anthropic）
- **语言：** Python 3.10+
- **测试：** pytest + pytest-json-report
- **CI：** GitHub Actions（flake8 + pytest，拦截过时的 `gpt-4` 字符串）
- **容器化：** Docker + docker-compose
- **配置管理：** pydantic-settings

---

## 文档

## 开发规范

**分支策略：**
- `main` — 仅用于稳定发布
- `dev` — 集成分支，所有 PR 合并至此
- `feature/<名称>` — 各智能体/功能开发分支

禁止直接推送至 `dev` 或 `main`，所有变更须通过 Pull Request 并由 M1 审核后合并。

**LLM 调用**记录至 `logs/llm_calls.jsonl`（包含时间戳、智能体、提供商、模型、Token 数、延迟）。运行 `python run.py stats` 查看汇总统计。
