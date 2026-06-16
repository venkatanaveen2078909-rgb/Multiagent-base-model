# `evaluation/benchmarks.py` — Line-by-Line Explanation

**File:** `evaluation/benchmarks.py`  
**Role:** Defines the benchmark test cases that form the "ground truth" test suite for evaluating agent performance via DeepEval.

---

## Imports and DeepEval Setup (Lines 17–31)

```python
try:
    from deepeval import evaluate
    # ... import metrics ...
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False
    import warnings
    warnings.warn("deepeval not installed. Using lightweight fallback evaluation.")
```

- Uses a try-except block for DeepEval. This is a defensive pattern: if DeepEval isn't installed, the file won't crash on import, it will just flag that DeepEval isn't available.

---

## BenchmarkCase Dataclass (Lines 34–41)

```python
@dataclass
class BenchmarkCase:
    """A single benchmark test case."""
    agent: str
    input: str
    expected_output_keywords: List[str]
    context: str = ""
    category: str = "general"
```

- Defines the schema for a test case. The critical field is `expected_output_keywords`, which provides a heuristic baseline for verifying the agent covered the core topics required by the input prompt.

---

## Benchmark Definitions (Lines 44–355)

```python
RESEARCH_BENCHMARKS: List[BenchmarkCase] = [
    BenchmarkCase("research_agent", "What is LangGraph and how does it work?",
                  ["LangGraph", "graph", "nodes", "state"], category="AI/ML"),
    # ... 19 more cases ...
]

CAREER_BENCHMARKS: List[BenchmarkCase] = [ ... ]
```

- Instantiates 20 `BenchmarkCase` objects per agent (80 in total).
- The Code Review section defines raw code strings in `_CODE_SAMPLES` containing known flaws (like SQL injection or N+1 query problems) and then passes those strings into the `BenchmarkCase` objects, verifying that the LLM identifies the specific vulnerability.

---

## Aggregation and Runner (Lines 361–386)

```python
ALL_BENCHMARKS = (
    RESEARCH_BENCHMARKS
    + CAREER_BENCHMARKS
    + CODE_REVIEW_BENCHMARKS
    + EVALUATOR_BENCHMARKS
)

def get_benchmarks_by_agent(agent_name: str) -> List[BenchmarkCase]:
    return [b for b in ALL_BENCHMARKS if b.agent == agent_name]

def count_by_agent() -> dict:
    from collections import Counter
    return dict(Counter(b.agent for b in ALL_BENCHMARKS))
```

- Combines all lists into `ALL_BENCHMARKS`.
- Provides lookup functions used by `main.py benchmark` and `tests/test_agents.py` to count and filter the test cases dynamically.

```python
if __name__ == "__main__":
    print("📊 Benchmark Summary")
    # ... prints counts ...
```

- Allows the file to be run directly (`python evaluation/benchmarks.py`) to print out the test case counts to the terminal.
