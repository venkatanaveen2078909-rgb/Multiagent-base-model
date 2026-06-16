"""
main.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Main entry points:

  # Start the API server
  python main.py serve

  # Run a one-off workflow from CLI
  python main.py run "What is LangGraph?"

  # Run benchmarks (unit tests only, no API)
  python main.py benchmark

  # Print platform info
  python main.py info
"""

import argparse
import asyncio
import sys
import io

# Ensure Unicode output works on Windows cp1252 terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def cmd_serve(args):
    """Start the FastAPI server."""
    import uvicorn
    from config import get_settings
    settings = get_settings()
    host = settings.api_host
    port = settings.api_port
    display_host = "localhost" if host in ("0.0.0.0", "127.0.0.1") else host

    print()
    print("=" * 56)
    print("  Agentic AI Platform")
    print("=" * 56)
    print(f"  Web UI  : http://{display_host}:{port}/")
    print(f"  API Docs: http://{display_host}:{port}/docs")
    print()
    print("  Keep this terminal open while using the UI.")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 56)
    print()

    uvicorn.run(
        "api.app:app",
        host=host,
        port=port,
        reload=settings.api_debug,
        log_level=settings.log_level.lower(),
    )


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
        # Safely print report — replace any chars the terminal can't encode
        report = state["final_report"] or ""
        sys.stdout.write(report + "\n")

    asyncio.run(_run())


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
    from config import get_settings
    s = get_settings()
    print(f"Web UI: http://{s.api_host if s.api_host != '0.0.0.0' else 'localhost'}:{s.api_port}/")
    print(f"API docs: http://localhost:{s.api_port}/docs")
    print()


def main():
    # Activate LangSmith tracing as early as possible
    from config import get_settings
    get_settings().configure_langsmith()

    parser = argparse.ArgumentParser(
        prog="agentic-platform",
        description="Agentic AI Platform CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI server")

    # run
    run_parser = subparsers.add_parser("run", help="Run a one-off workflow")
    run_parser.add_argument("input", help="User input / query")

    # benchmark
    bench_parser = subparsers.add_parser("benchmark", help="Show benchmark summary")

    # info
    info_parser = subparsers.add_parser("info", help="Show platform info")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "benchmark":
        cmd_benchmark(args)
    elif args.command == "info":
        cmd_info(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()