# `agents/code_review_agent.py` — Line-by-Line Explanation

**File:** `agents/code_review_agent.py`  
**Role:** Implements the `CodeReviewAgent`, which analyses code snippets for correctness, performance, security, and stylistic issues, providing a production-grade review.

---

## Class Definition and Init (Lines 26–48)

```python
class CodeReviewAgent(BaseAgent):
    """
    Performs production-grade code review across multiple quality dimensions.
    """

    agent_name = "code_review_agent"
    version = "1.0"

    def __init__(
        self,
        prompt_version: Optional[str] = None,
        strictness_level: str = "standard",
        security_focus: bool = True,
        performance_focus: bool = True,
        explanation_detail: str = "standard",
        temperature: float = 0.1,  # Very low for deterministic reviews
    ):
        super().__init__(prompt_version=prompt_version, temperature=temperature)

        self.strictness_level = strictness_level
        self.security_focus = security_focus
        self.performance_focus = performance_focus
        self.explanation_detail = explanation_detail
```

- **Inherits from `BaseAgent`**.
- **`__init__`**: 
  - Sets parameters like `strictness_level`, `security_focus`, etc.
  - Hardcodes a default `temperature` of `0.1`. A very low temperature is crucial here because code review demands high determinism, factual accuracy, and strict adherence to structural formats rather than creative writing.

---

## Language Detection Heuristic (Lines 50–59)

```python
    @staticmethod
    def _detect_language(code: str) -> str:
        """Heuristic language detection from code content."""
        if re.search(r"\bdef \w+\(|import \w+|print\(", code):
            return "Python"
        if re.search(r"function \w+\(|const |let |var ", code):
            return "JavaScript"
        if re.search(r"#include|int main\(|std::", code):
            return "C++"
        return "Unknown"
```

- **`@staticmethod`**: Indicates this function doesn't require access to instance (`self`) variables.
- Uses basic regular expressions to scan the code snippet and guess the programming language. This allows the API to gracefully handle code submissions where the language isn't explicitly provided by the user.

---

## Context Builder `_build_review_context` (Lines 61–97)

```python
    def _build_review_context(
        self,
        language: str,
        strictness: str,
        security: bool,
        performance: bool,
        detail: str,
    ) -> str:
        """Build the configuration block appended to the system prompt."""
        focus_areas = []
        if security:
            focus_areas.append("Pay special attention to security vulnerabilities.")
        if performance:
            focus_areas.append("Pay special attention to performance bottlenecks.")
        
        # ... dictionary mappings for strictness and detail ...

        return (
            f"\n\nREVIEW CONFIGURATION:\n"
            f"- Language: {language}\n"
            f"- Strictness: {strictness} — {strictness_map.get(strictness, '')}\n"
            f"- Explanation Detail: {detail} — {detail_map.get(detail, '')}\n"
            + ("\n".join(f"- {f}" for f in focus_areas) if focus_areas else "")
        )
```

- Maps boolean flags (`security`, `performance`) and string tiers (`strictness`, `detail`) into concrete English instructions.
- Returns a formatted string that will be appended to the end of the system prompt to dynamically alter the reviewer's focus and output verbosity.

---

## Execution Method `run` (Lines 99–189)

```python
    async def run(
        self,
        task: str,
        strictness_level: Optional[str] = None,
        # ... other overrides ...
        language: Optional[str] = None,
        **kwargs,
    ) -> AgentOutput:
        start = time.perf_counter()

        # Resolve parameters ...
        detected_lang = language or self._detect_language(task)
```

- Standard override pattern: uses method arguments if provided, otherwise falls back to the instance attributes initialized in `__init__`.
- **`detected_lang`**: If the caller didn't specify a language, it uses the heuristic method `_detect_language` on the `task` (which is the code string).

```python
        try:
            context = self._build_review_context(
                detected_lang, strict, sec, perf, detail
            )
            augmented_system = self.system_prompt + context

            messages = [
                SystemMessage(content=augmented_system),
                HumanMessage(
                    content=(
                        f"Please review the following {detected_lang} code:\n\n"
                        f"```{detected_lang.lower()}\n{task}\n```"
                    )
                ),
            ]

            response = await self.llm.ainvoke(messages)
            result = response.content
```

- Appends the configuration string to the static system prompt.
- Wraps the user's code inside a markdown code block tagged with the detected language. This helps the LLM parse and understand the input structure better.
- Executes the LLM call asynchronously.

```python
            return AgentOutput(
                agent_name=self.agent_name,
                version=self.version,
                prompt_version=self.prompt_version,
                task=f"Code review ({detected_lang}, {len(task)} chars)",
                result=result,
                metadata={
                    "language": detected_lang,
                    "strictness_level": strict,
                    "security_focus": sec,
                    "performance_focus": perf,
                    "explanation_detail": detail,
                    "code_length": len(task),
                },
                latency_ms=latency,
                success=True,
            )
```

- Constructs the `AgentOutput`.
- **`task` summary**: Instead of returning the entire block of code as the task (which would bloat the database), it summarizes the task as `"Code review (Python, 450 chars)"`.
- **`metadata`**: Captures all specific review settings and the character count for analytics.
