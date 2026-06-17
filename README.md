# Agentic AI Platform

A production-ready multi-agent system built with **LangGraph**, **LangChain**, **LangSmith**, **Groq**, **Tavily**, and **FastAPI**.

---

## Architecture

```
User Request
     │
     ▼
┌────────────┐
│ Supervisor │  (routes via LLM JSON decision)
└─────┬──────┘
      │
      ├──────────────────┬──────────────────┐
      ▼                  ▼                  ▼
┌──────────────┐  ┌─────────────┐  ┌──────────────────┐
│ Research     │  │  Career     │  │ Code Review      │
│ Agent        │  │  Agent      │  │ Agent            │
│ (Tavily)     │  │             │  │                  │
└──────┬───────┘  └──────┬──────┘  └────────┬─────────┘
       └──────────────────┴──────────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │  Evaluator    │
                  │  Agent        │
                  └───────┬───────┘
                          │
                          ▼
                    Final Report
```

---

## Agents

| Agent | Responsibility | Key Tools |
|-------|---------------|-----------|
| **Supervisor** | Routes requests to the right agent | Groq LLM |
| **Research** | Web research + structured reports | Tavily Search |
| **Career** | Resume analysis + career roadmaps | Groq LLM |
| **Code Review** | Bug detection, security, performance | Groq LLM |
| **Evaluator** | Scores all other agent outputs | Groq LLM |

---

## Project Structure

```
agentic_ai_platform/
├── agents/
│   ├── base.py               # Abstract base class + AgentOutput
│   ├── research_agent.py     # Web research + Tavily
│   ├── career_agent.py       # Career guidance
│   ├── code_review_agent.py  # Code analysis
│   └── evaluator_agent.py    # Quality scoring
├── graph/
│   └── workflow.py           # LangGraph StateGraph orchestration
├── prompts/
│   └── prompt_registry.py    # Versioned prompts (v1/v2/v3 per agent)
├── evaluation/
│   ├── benchmarks.py         # 80 benchmark test cases (20 per agent)
│   └── reports.py            # Certification + tuning reports
├── api/
│   └── app.py                # FastAPI REST endpoints
├── tests/
│   └── test_agents.py        # pytest + DeepEval test suite
├── config.py                 # Pydantic settings from .env
├── database.py               # Async SQLAlchemy (SQLite/PostgreSQL)
├── main.py                   # CLI entry point
├── requirements.txt
└── .env.example
```

---

## Installation

### 1. Clone and install

```bash
git clone <repo-url>
cd agentic_ai_platform
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys:
#   GROQ_API_KEY      — https://console.groq.com
#   GROQ_MODEL        — openai/gpt-oss-120b
#   TAVILY_API_KEY    — https://tavily.com
#   LANGSMITH_API_KEY — https://smith.langchain.com
```

### 3. Start the API server

```bash
python main.py serve
# → http://localhost:8000/docs
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/run` | Full multi-agent workflow |
| `POST` | `/agents/research` | Research agent directly |
| `POST` | `/agents/career` | Career agent directly |
| `POST` | `/agents/code-review` | Code review agent directly |
| `POST` | `/evaluate` | Evaluate any text output |
| `GET`  | `/runs` | List recent runs |
| `GET`  | `/runs/{id}` | Single run + evaluation |
| `GET`  | `/prompts` | All prompt versions |
| `POST` | `/prompts/compare` | Compare two versions |
| `GET`  | `/health` | Health check |

### Quick Examples

```bash
# Full workflow
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"user_input": "What is retrieval-augmented generation?"}'

# Research directly with params
curl -X POST http://localhost:8000/agents/research \
  -H "Content-Type: application/json" \
  -d '{"task": "LangGraph architecture", "search_depth": "advanced", "max_results": 7}'

# Career guidance
curl -X POST http://localhost:8000/agents/career \
  -H "Content-Type: application/json" \
  -d '{"task": "I am a 3rd year CS student...", "career_target": "AI Engineer"}'

# Code review
curl -X POST http://localhost:8000/agents/code-review \
  -H "Content-Type: application/json" \
  -d '{"code": "def get_user(name):\n    return db.execute(f\"SELECT * FROM users WHERE name={name}\")"}'
```

---

## CLI Usage

```bash
# Start server
python main.py serve

# Run a one-off query
python main.py run "Explain transformer architecture"

# Show benchmark summary
python main.py benchmark

# Show platform info
python main.py info
```

---

## Running Tests

```bash
# All tests (unit + integration)
pytest tests/ -v

# Unit tests only (no API keys needed)
pytest tests/ -v -k "unit or TestPromptRegistry or TestBenchmarkCoverage or TestReportGeneration"

# By agent
pytest tests/ -v -k "research"
pytest tests/ -v -k "career"
pytest tests/ -v -k "code_review"
pytest tests/ -v -k "evaluator"
```

---

## Prompt Tuning

Each agent has versioned prompts in `prompts/prompt_registry.py`.

| Agent | Versions | Notes |
|-------|----------|-------|
| Research | v1, v2, v3 | v3 = best; sub-questions, confidence, gaps |
| Career | v1, v2 | v2 = prioritised gaps + detailed roadmap |
| Code Review | v1, v2 | v2 = FAANG-level, severity labels, OWASP |
| Evaluator | v1, v2 | v2 = rubrics, evidence-based, detailed |

To run an agent with a specific prompt version:

```python
agent = ResearchAgent(prompt_version="v2")
```

To compare versions via API:
```bash
curl -X POST http://localhost:8000/prompts/compare \
  -d '{"agent": "research_agent", "version_a": "v1", "version_b": "v3"}'
```

---

## Evaluation Metrics

Every agent output is automatically evaluated on:

| Metric | Scale | Description |
|--------|-------|-------------|
| Accuracy | 0–10 | Factual correctness |
| Completeness | 0–10 | Task coverage |
| Relevance | 0–10 | On-topic quality |
| Structure | 0–10 | Formatting & organisation |
| Tool Usage Quality | 0–10 | Appropriate tool use |
| Hallucination Risk | Low/Med/High | Unsupported claims |
| **Overall Score** | **0–100** | **Weighted composite** |

**Certification thresholds:**
- ✅ PASS: Score ≥ 80
- ⚠️ CONDITIONAL PASS: Score 65–79
- ❌ FAIL: Score < 65

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Groq (openai/gpt-oss-120b) |
| Orchestration | LangGraph StateGraph |
| Agent Framework | LangChain |
| Web Search | Tavily |
| API | FastAPI + uvicorn |
| Observability | LangSmith |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Evaluation | DeepEval |
| Logging | structlog |
| Config | Pydantic Settings |
| Testing | pytest + pytest-asyncio |

---

## License

MIT