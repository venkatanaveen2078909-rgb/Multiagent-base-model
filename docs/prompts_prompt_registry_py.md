# `prompts/prompt_registry.py` — Line-by-Line Explanation

**File:** `prompts/prompt_registry.py`  
**Role:** Centralised system for managing, versioning, and fetching the system prompts used by the LLMs across all agents.

---

## PromptRecord Dataclass (Lines 26–32)

```python
@dataclass
class PromptRecord:
    agent: str
    version: str
    system_prompt: str
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
```

- A simple structure holding all metadata for a single prompt version.
- `notes` is useful for tracking *why* a prompt was changed (e.g., "Added CoT reasoning").
- `created_at` automatically populates with the UTC timestamp when the record is instantiated.

---

## Static Prompts (Lines 35–432)

```python
_RESEARCH_V1 = """..."""
_RESEARCH_V2 = """..."""
# ... many more multi-line strings ...
```

- These constants hold the raw text strings for every prompt version.
- Storing them here directly in Python (rather than a database) ensures they are strictly version-controlled in Git alongside the code that depends on them.

---

## Registry Dictionary and Defaults (Lines 438–468)

```python
_REGISTRY: Dict[str, Dict[str, PromptRecord]] = {
    "research_agent": {
        "v1": PromptRecord("research_agent", "v1", _RESEARCH_V1, "Initial prompt"),
        "v2": PromptRecord("research_agent", "v2", _RESEARCH_V2, "Added confidence scoring + CoT"),
        "v3": PromptRecord("research_agent", "v3", _RESEARCH_V3, "World-class analyst persona, sub-questions, knowledge gaps"),
    },
    # ... other agents ...
}

_DEFAULTS: Dict[str, str] = {
    "research_agent": "v3",
    "career_agent": "v2",
    "code_review_agent": "v2",
    "evaluator_agent": "v2",
    "supervisor_agent": "v1",
}
```

- `_REGISTRY`: A nested dictionary mapping `agent_name -> version_string -> PromptRecord`.
- `_DEFAULTS`: Specifies which version should be used if the caller doesn't explicitly ask for one. This makes A/B testing simple—just change the default to a new version and let the test suite run.

---

## PromptRegistry Class (Lines 471–528)

```python
class PromptRegistry:
    """Manages versioned prompts for all agents."""

    def get(self, agent: str, version: Optional[str] = None) -> PromptRecord:
        if agent not in _REGISTRY:
            raise KeyError(f"Unknown agent: {agent!r}. Available: {self.all_agents()}")
        version = version or _DEFAULTS[agent]
        if version not in _REGISTRY[agent]:
            raise KeyError(...)
        return _REGISTRY[agent][version]
```

- **`get`**: Safely retrieves a prompt. If `version` is `None`, it looks up the default in `_DEFAULTS`. Raises clear `KeyError` exceptions if typos are made.

```python
    def list_versions(self, agent: str) -> List[str]: ...
    def all_agents(self) -> List[str]: ...
```

- Helper methods used heavily by `main.py info` and the FastAPI `/prompts` endpoint to introspect the registry.

```python
    def compare(self, agent: str, v1: str, v2: str) -> dict:
        """Return side-by-side comparison dict for tuning reports."""
        r1 = self.get(agent, v1)
        r2 = self.get(agent, v2)
        return {
            "agent": agent,
            "version_a": {"version": v1, "notes": r1.notes, "prompt": r1.system_prompt},
            "version_b": {"version": v2, "notes": r2.notes, "prompt": r2.system_prompt},
        }
```

- Used by the `/prompts/compare` endpoint to return JSON payloads suitable for frontend UI tools that render diffs between two prompts.
