# `agents/career_agent.py` — Line-by-Line Explanation

**File:** `agents/career_agent.py`  
**Role:** Implements the `CareerAgent`, which analyses resumes and profiles, identifies skill gaps, and generates personalised career roadmaps based on user context.

---

## Class Definition and Init (Lines 24–47)

```python
class CareerAgent(BaseAgent):
    """
    Provides personalised career guidance including skill gap analysis
    and concrete roadmaps tailored to the user's background.
    """

    agent_name = "career_agent"
    version = "1.0"

    def __init__(
        self,
        prompt_version: Optional[str] = None,
        experience_level: str = "student",
        career_target: str = "AI/ML Engineer",
        industry_focus: str = "AI startups",
        recommendation_depth: str = "standard",
        temperature: float = 0.4,  # Slightly higher for creative roadmap generation
    ):
        super().__init__(prompt_version=prompt_version, temperature=temperature)

        self.experience_level = experience_level
        self.career_target = career_target
        self.industry_focus = industry_focus
        self.recommendation_depth = recommendation_depth
```

- **Inherits from `BaseAgent`**: Gives it access to standard LLM initialization, logging, and performance timing.
- **Attributes `agent_name` and `version`**: Identifies the agent. The name must match the key used in the `PromptRegistry`.
- **`__init__`**: 
  - Sets default values for the career parameters (e.g., student aiming for AI/ML Engineer in startups).
  - Uses `temperature=0.4` as the default, which is slightly higher than other agents, allowing for more creative and diverse advice generation.
  - Calls `super().__init__` to initialize the LLM and fetch the prompt.
  - Saves the specific career parameters as instance attributes.

---

## Context Builder `_build_context_block` (Lines 49–72)

```python
    def _build_context_block(
        self,
        experience_level: str,
        career_target: str,
        industry_focus: str,
        recommendation_depth: str,
    ) -> str:
        """Build a context block appended to the system prompt."""
        depth_instructions = {
            "shallow": "Provide a high-level overview. Keep recommendations concise.",
            "standard": "Provide a balanced, actionable analysis with specific steps.",
            "deep": (
                "Provide an exhaustive analysis. Include specific course names, "
                "project ideas, company names, and week-by-week action items where possible."
            ),
        }
        return (
            f"\n\nUSER CONTEXT:\n"
            f"- Experience Level: {experience_level}\n"
            f"- Career Target: {career_target}\n"
            f"- Industry Focus: {industry_focus}\n"
            f"- Analysis Depth: {recommendation_depth}\n"
            f"- Instruction: {depth_instructions.get(recommendation_depth, '')}"
        )
```

- **`depth_instructions`**: Maps the `recommendation_depth` parameter to a specific string of instructions for the LLM.
- **Returns**: A formatted string summarizing the user context. This string will be appended to the base system prompt to dynamically tailor the LLM's behavior to the user's specific scenario.

---

## Execution Method `run` (Lines 74–156)

```python
    async def run(
        self,
        task: str,
        experience_level: Optional[str] = None,
        career_target: Optional[str] = None,
        industry_focus: Optional[str] = None,
        recommendation_depth: Optional[str] = None,
        **kwargs,
    ) -> AgentOutput:
        """...docstring..."""
        start = time.perf_counter()

        # Parameter resolution
        exp   = experience_level    or self.experience_level
        target = career_target      or self.career_target
        ind   = industry_focus      or self.industry_focus
        depth = recommendation_depth or self.recommendation_depth

        self.log.info(
            "career_agent.run",
            experience=exp,
            target=target,
            industry=ind,
            depth=depth,
        )
```

- **`async def run`**: The main coroutine called to process a request.
- **`start = time.perf_counter()`**: Records the start time to calculate latency later.
- **Parameter resolution**: For each parameter, it uses the passed argument if provided, otherwise it falls back to the instance default.
- **`self.log.info(...)`**: Logs the invocation with the resolved parameters using the structured logger.

```python
        try:
            context_block = self._build_context_block(exp, target, ind, depth)
            augmented_system = self.system_prompt + context_block

            messages = [
                SystemMessage(content=augmented_system),
                HumanMessage(
                    content=(
                        f"Please analyse the following profile and provide career guidance:\n\n"
                        f"{task}"
                    )
                ),
            ]

            response = await self.llm.ainvoke(messages)
            result = response.content

            latency = self._time_it(start)
            self.log.info("career_agent.done", latency_ms=latency)
```

- **`augmented_system`**: Combines the static system prompt (from the registry) with the dynamic user context block.
- **`messages`**: Creates the LangChain message payload containing the `SystemMessage` and the `HumanMessage` (which includes the user's task/resume).
- **`await self.llm.ainvoke(messages)`**: Makes the asynchronous call to the LLM.
- **`latency`**: Calculates the elapsed time in ms.
- **`self.log.info("career_agent.done"...)`**: Logs successful completion.

```python
            return AgentOutput(
                agent_name=self.agent_name,
                version=self.version,
                prompt_version=self.prompt_version,
                task=task[:200] + "..." if len(task) > 200 else task,
                result=result,
                metadata={
                    "experience_level": exp,
                    "career_target": target,
                    "industry_focus": ind,
                    "recommendation_depth": depth,
                },
                latency_ms=latency,
                success=True,
            )

        except Exception as exc:
            self.log.error("career_agent.error", error=str(exc))
            return AgentOutput(
                ... # error output fields
                success=False,
                error=str(exc),
            )
```

- **`return AgentOutput(...)`**: Packages the response into the standardized data structure.
  - **`task`**: Truncates the input task to 200 characters to prevent huge database records if the user submits a massive resume.
  - **`metadata`**: Includes all the resolved career parameters for analytics/reporting.
- **`except Exception as exc`**: Catches any LLM or network errors, logs them, and returns an `AgentOutput` with `success=False` and the error message attached, ensuring the system doesn't crash from a transient API failure.
