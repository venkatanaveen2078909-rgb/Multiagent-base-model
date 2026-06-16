"""Quick smoke test for all API endpoints."""
import httpx
import json

base = "http://127.0.0.1:8001"

# 1. Health
r = httpx.get(f"{base}/health", timeout=10)
print("=== /health ===")
print(json.dumps(r.json(), indent=2))
assert r.status_code == 200
assert r.json()["status"] == "ok"
print("  PASS\n")

# 2. Runs (empty DB is fine)
r = httpx.get(f"{base}/runs", timeout=10)
print("=== /runs ===")
print(json.dumps(r.json(), indent=2))
assert r.status_code == 200
assert isinstance(r.json(), list)
print("  PASS\n")

# 3. Prompts registry
r = httpx.get(f"{base}/prompts", timeout=10)
print("=== /prompts ===")
data = r.json()
for agent, versions in data.items():
    print(f"  {agent}: {[v['version'] for v in versions]}")
assert r.status_code == 200
assert "research_agent" in data
assert "career_agent" in data
assert "code_review_agent" in data
print("  PASS\n")

# 4. Prompt compare
r = httpx.post(
    f"{base}/prompts/compare",
    json={"agent": "research_agent", "version_a": "v1", "version_b": "v3"},
    timeout=10,
)
print("=== /prompts/compare ===")
cmp = r.json()
print(f"  version_a: {cmp['version_a']['version']}, version_b: {cmp['version_b']['version']}")
assert r.status_code == 200
assert cmp["version_a"]["version"] == "v1"
assert cmp["version_b"]["version"] == "v3"
print("  PASS\n")

# 5. /evaluate with a synthetic output
r = httpx.post(
    f"{base}/evaluate",
    json={
        "agent_output_text": "Python is a high-level, interpreted programming language known for its simplicity.",
        "agent_name": "research_agent",
        "prompt_version": "v3",
        "task": "What is Python?",
    },
    timeout=60,
)
print("=== /evaluate ===")
ev = r.json()
print(json.dumps(ev, indent=2))
assert r.status_code == 200
assert "overall_score" in ev
print("  PASS\n")

print("=" * 50)
print("ALL ENDPOINT SMOKE TESTS PASSED")
