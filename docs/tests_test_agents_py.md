# `tests/test_agents.py` — Line-by-Line Explanation

**File:** `tests/test_agents.py`  
**Role:** The pytest suite containing both unit tests (fast, no network) and integration tests (slow, requires LLM API calls) to verify the platform.

---

## Setup and Imports (Lines 20–48)

```python
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
```

- Standard Python test hack to ensure the root `AGI Architecture` directory is in the import path, allowing `import agents` to work without installing the project as a package.

---

## Unit Tests (Lines 51–128)

```python
class TestPromptRegistry:
    def test_all_agents_have_prompts(self):
        r = PromptRegistry()
        agents = r.all_agents()
        assert "research_agent" in agents
        # ...
```

- **`TestPromptRegistry`**: Verifies that the dictionary in `prompt_registry.py` is configured correctly—all agents exist, version defaults point to valid keys, and comparison outputs match correctly.
- **`TestBenchmarkCoverage`**: Hard-asserts that there are exactly 20 test cases per agent in the `benchmarks.py` file to prevent accidental deletion of test coverage.
- **`TestReportGeneration`**: Tests that the math and string formatting inside `reports.py` works correctly even when fed empty data.

*These tests run in milliseconds and cost $0.*

---

## Integration Tests Environment Guard (Lines 134–138)

```python
requires_api = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping API integration tests",
)
```

- Uses pytest markers. Any test class tagged with `@requires_api` will be completely skipped if the `GROQ_API_KEY` environment variable isn't found. This prevents the CI pipeline from crashing purely due to missing secrets.

---

## Agent Integration Tests (Lines 141–266)

```python
@requires_api
class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_basic_research(self):
        agent = ResearchAgent(search_depth="basic", max_results=3)
        output = await agent.run("What is LangGraph?")
        assert output.success
        assert len(output.result) > 100
        assert output.agent_name == "research_agent"
```

- **`@pytest.mark.asyncio`**: Required because the test functions call async coroutines (`await agent.run(...)`).
- These tests actually hit the Groq/Tavily APIs.
- They assert that the network call succeeded (`output.success`), the result has length, and the metadata matches the inputs.

```python
    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", RESEARCH_BENCHMARKS[:3])
    async def test_benchmark_cases(self, case: BenchmarkCase):
        agent = ResearchAgent(search_depth="basic", max_results=3)
        output = await agent.run(case.input)
        
        found = [kw for kw in case.expected_output_keywords if kw.lower() in output.result.lower()]
        assert len(found) >= len(case.expected_output_keywords) // 2
```

- **`@pytest.mark.parametrize`**: A powerful pytest feature. It runs this test function multiple times, looping over the first 3 items in `RESEARCH_BENCHMARKS`.
- Rather than full DeepEval, this does a lightweight assertion: it requires at least 50% (`// 2`) of the `expected_output_keywords` to appear in the LLM's response.

```python
@requires_api
class TestCodeReviewAgent:
    @pytest.mark.asyncio
    async def test_detects_sql_injection(self):
        # ... runs code agent over SQL injection string ...
        assert any(kw in output.result.lower() for kw in ["sql injection", "sql", "injection"])
```

- Specifically checks if the Code Review agent's prompt successfully identifies the security flaw injected into the code snippet.

```python
@requires_api
class TestEvaluatorAgent:
    @pytest.mark.asyncio
    async def test_evaluation_returns_scores(self):
        # ... feeds a fake output into the evaluator ...
        assert 0 <= result.accuracy <= 10
        assert result.certification_status in ("PASS", "CONDITIONAL PASS", "FAIL")
```

- Feeds mocked AgentOutputs into the Evaluator to ensure its regex parsing logic works against live LLM formatting.
