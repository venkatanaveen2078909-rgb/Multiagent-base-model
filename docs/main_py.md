# `main.py` — Line-by-Line Explanation

**File:** `main.py`  
**Role:** CLI entry point for the entire Agentic AI Platform. Lets you start the API server, run a one-off workflow, show benchmarks, or inspect registered agents — all from the terminal.

---

## Module Docstring (Lines 1–17)

```python
"""
main.py
...
"""
```

Top-level module docstring. Documents the four CLI sub-commands that this file provides:
- `python main.py serve` → starts the FastAPI HTTP server
- `python main.py run "query"` → runs a single workflow end-to-end from the terminal
- `python main.py benchmark` → prints a summary of how many test cases exist per agent
- `python main.py info` → prints registered agents and their prompt versions

---

## Imports (Lines 19–22)

```python
import argparse   # stdlib: parses CLI arguments
import asyncio    # stdlib: runs async functions from synchronous main()
import sys        # stdlib: access to stdout and exit codes
import io         # stdlib: imported but unused directly here (safe to ignore)
```

---

## Windows Unicode Fix (Lines 24–26)

```python
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

Windows terminals default to `cp1252` encoding, which cannot render many Unicode characters (emoji, special arrows, etc.). This block:
1. **Checks** whether `stdout` supports `reconfigure` (it does in Python 3.7+ on Windows).
2. **Switches** stdout to UTF-8 so the final report's emoji (✅, ⚠️, ❌) print correctly.
3. **Uses `errors="replace"`** so that any character that still can't be encoded is silently replaced rather than crashing.

---

## `cmd_serve(args)` — Lines 29–41

```python
def cmd_serve(args):
    """Start the FastAPI server."""
    import uvicorn
    from config import get_settings
    settings = get_settings()
    print(f"Starting Agentic AI Platform API on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        log_level=settings.log_level.lower(),
    )
```

| Line | What it does |
|------|-------------|
| `import uvicorn` | Lazy import — only loaded when this sub-command is chosen. Keeps startup fast for other commands. |
| `from config import get_settings` | Pulls the cached `Settings` singleton (host, port, debug mode). |
| `settings = get_settings()` | Reads `.env` values once via `lru_cache`. |
| `uvicorn.run("api.app:app", ...)` | Starts the ASGI server. The string `"api.app:app"` tells uvicorn to import `app` from the `api/app.py` module. |
| `reload=settings.api_debug` | When `API_DEBUG=true` in `.env`, uvicorn watches files and hot-reloads on change. |
| `log_level=settings.log_level.lower()` | Maps e.g. `"INFO"` → `"info"` for uvicorn's logger. |

---

## `cmd_run(args)` — Lines 44–59

```python
def cmd_run(args):
    """Run a one-off workflow from the CLI."""
    from graph.workflow import run_workflow

    async def _run():
        print(f"\nRunning workflow for: {args.input!r}\n")
        state = await run_workflow(args.input)
        print("=" * 60)
        print(f"Selected Agent : {state['selected_agent']}")
        print(f"Task Summary   : {state['task_summary']}")
        print("=" * 60)
        report = state["final_report"] or ""
        sys.stdout.write(report + "\n")

    asyncio.run(_run())
```

| Line | What it does |
|------|-------------|
| `from graph.workflow import run_workflow` | Lazy import of the LangGraph workflow runner. |
| `async def _run()` | Defines an inner async function because `run_workflow` is a coroutine. |
| `state = await run_workflow(args.input)` | Runs the full supervisor → specialist → evaluator pipeline and returns the final `GraphState` dict. |
| `state['selected_agent']` | Which specialist was chosen (e.g. `"research_agent"`). |
| `state['task_summary']` | The reformulated task that the supervisor handed to the specialist. |
| `sys.stdout.write(report + "\n")` | Uses `write()` instead of `print()` to respect the UTF-8 reconfiguration done earlier and avoid double newlines. |
| `asyncio.run(_run())` | Bridges the synchronous CLI world into the async coroutine world. |

---

## `cmd_benchmark(args)` — Lines 62–72

```python
def cmd_benchmark(args):
    """Print benchmark summary (no API calls needed)."""
    from evaluation.benchmarks import count_by_agent, ALL_BENCHMARKS

    print("\nBenchmark Test Suite Summary")
    print("=" * 42)
    for agent, count in sorted(count_by_agent().items()):
        print(f"  {agent:<30} {count:>3} test cases")
    print(f"  {'-'*38}")
    print(f"  {'TOTAL':<30} {len(ALL_BENCHMARKS):>3} test cases")
    print("\nRun tests with: pytest tests/ -v")
```

| Line | What it does |
|------|-------------|
| `count_by_agent()` | Returns a `dict[agent_name → count]` by counting `BenchmarkCase` objects grouped by `.agent`. |
| `ALL_BENCHMARKS` | Flat list of all 80 `BenchmarkCase` objects (20 per agent × 4 agents). |
| `sorted(...)` | Alphabetical ordering for consistent output. |
| `{agent:<30}` | Left-aligned, padded to 30 characters for a neat table. |
| `{count:>3}` | Right-aligned, padded to 3 digits. |

---

## `cmd_info(args)` — Lines 75–90

```python
def cmd_info(args):
    """Print platform info and registered agents."""
    from prompts.prompt_registry import PromptRegistry

    registry = PromptRegistry()
    print("\nAgentic AI Platform v1.0")
    print("=" * 42)
    print("Registered Agents & Prompt Versions:")
    for agent in registry.all_agents():
        versions = registry.list_versions(agent)
        default = registry.get(agent).version
        print(f"  {agent:<28} {', '.join(versions)}  (default: {default})")

    print("\nGraph: supervisor -> [research|career|code_review] -> evaluator -> END")
    print("API docs: http://localhost:8000/docs  (after starting server)")
    print()
```

| Line | What it does |
|------|-------------|
| `PromptRegistry()` | Instantiates the in-memory prompt registry (no DB or network needed). |
| `registry.all_agents()` | Returns `["research_agent", "career_agent", "code_review_agent", "evaluator_agent", "supervisor_agent"]`. |
| `registry.list_versions(agent)` | Returns e.g. `["v1", "v2", "v3"]` for `research_agent`. |
| `registry.get(agent).version` | Fetches the **default** prompt record and reads its version string. |
| The diagram line | Quickly summarises the graph topology for developers. |

---

## `main()` — Lines 93–125

```python
def main():
    parser = argparse.ArgumentParser(
        prog="agentic-platform",
        description="Agentic AI Platform CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser  = subparsers.add_parser("serve",     help="Start the FastAPI server")
    run_parser    = subparsers.add_parser("run",       help="Run a one-off workflow")
    run_parser.add_argument("input", help="User input / query")
    bench_parser  = subparsers.add_parser("benchmark", help="Show benchmark summary")
    info_parser   = subparsers.add_parser("info",      help="Show platform info")

    args = parser.parse_args()

    if   args.command == "serve":     cmd_serve(args)
    elif args.command == "run":       cmd_run(args)
    elif args.command == "benchmark": cmd_benchmark(args)
    elif args.command == "info":      cmd_info(args)
    else:
        parser.print_help()
        sys.exit(1)
```

| Line | What it does |
|------|-------------|
| `argparse.ArgumentParser(prog=..., description=...)` | Creates the top-level argument parser. `prog` sets the name shown in help text. |
| `add_subparsers(dest="command", required=True)` | Makes `args.command` hold the chosen sub-command name. `required=True` means the user _must_ supply one. |
| `add_parser("run")` + `add_argument("input", ...)` | `run` takes a positional argument: the user's query string. |
| `if/elif` chain | Dispatches to the correct `cmd_*` function based on which sub-command was chosen. |
| `sys.exit(1)` | Unreachable in normal flow (argparse handles unknown commands), but serves as a safety fallback. |

---

## Entry Guard (Lines 128–129)

```python
if __name__ == "__main__":
    main()
```

Standard Python idiom. `main()` is only called when the file is executed directly (`python main.py …`). When another module imports `main.py`, the CLI is **not** triggered.
