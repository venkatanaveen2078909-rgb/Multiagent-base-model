# `requirements.txt` — Line-by-Line Explanation

**File:** `requirements.txt`  
**Role:** Specifies all external Python dependencies required to run the application, locked to minimum versions to ensure stability.

---

## Core LLM & Agent Stack (Lines 1–6)

```text
# Core LLM & Agent Stack
langchain>=0.2.0
langchain-core>=0.2.0
langchain-groq>=0.1.0
langchain-community>=0.2.0
langgraph>=0.1.0
```

- **`langchain` / `langchain-core`**: The foundational frameworks for building LLM applications, managing message prompts, and memory.
- **`langchain-groq`**: The specific provider package for Groq's extremely fast inference APIs.
- **`langchain-community`**: Contains third-party tool integrations (like Tavily).
- **`langgraph`**: The state-machine orchestrator used to build the supervisor/specialist/evaluator routing graph in `workflow.py`.

---

## Search (Lines 8–9)

```text
# Search
tavily-python>=0.3.0
```

- **`tavily-python`**: The official SDK for the Tavily search engine, which is built specifically for AI agents to retrieve structured facts rather than just web links.

---

## API (Lines 11–14)

```text
# API
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
python-multipart>=0.0.9
```

- **`fastapi`**: The web framework used in `api/app.py`.
- **`uvicorn[standard]`**: The ASGI server that runs the FastAPI app asynchronously.
- **`python-multipart`**: Enables FastAPI to parse form data and file uploads (even if unused currently, it's standard FastAPI boilerplate).

---

## Database (Lines 16–18)

```text
# Database
sqlalchemy>=2.0.0
aiosqlite>=0.20.0
```

- **`sqlalchemy`**: The Object Relational Mapper (ORM). Version 2.0+ is required for the new async APIs.
- **`aiosqlite`**: The async driver for SQLite. Without this, SQLAlchemy would block the FastAPI event loop when reading/writing to the database.

---

## Evaluation (Lines 20–21)

```text
# Evaluation
deepeval>=1.0.0
```

- **`deepeval`**: An open-source evaluation framework for LLMs used in `benchmarks.py`.

---

## Utilities (Lines 23–29)

```text
# Utilities
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
httpx>=0.27.0
tenacity>=8.3.0
structlog>=24.1.0
```

- **`pydantic`**: Data validation framework.
- **`pydantic-settings` & `python-dotenv`**: Responsible for reading `.env` and safely injecting it into `config.py`.
- **`httpx`**: Async HTTP client (used under the hood by LangChain and Groq).
- **`tenacity`**: Retrying library (helpful for API rate limits).
- **`structlog`**: Advanced logging framework that forces logs into structured key-value pairs (`agent="research" latency=230`), making them easy to parse in Datadog/CloudWatch.

---

## Testing (Lines 31–33)

```text
# Testing
pytest>=8.2.0
pytest-asyncio>=0.23.0
```

- **`pytest`**: The test runner.
- **`pytest-asyncio`**: Plugin that allows writing `async def test_...` to test asynchronous code.
