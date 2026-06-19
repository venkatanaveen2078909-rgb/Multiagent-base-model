# Kill Switch — Emergency Agent Shutdown

## Purpose

This runbook describes how to immediately disable the Agentic AI Platform in an emergency (e.g., the agent is producing harmful outputs, data breach detected, or runaway costs).

## Severity Levels

| Level | Trigger | Action |
|-------|---------|--------|
| **SEV-1** | Agent producing harmful/toxic content | Immediate full shutdown |
| **SEV-2** | Data leakage or PII exposure detected | Disable affected endpoints |
| **SEV-3** | Cost runaway (exceeding budget) | Disable external API calls |

## Emergency Shutdown Steps

### Option 1: Full Shutdown (SEV-1)

```bash
# Stop the FastAPI server immediately
# If running via systemd
sudo systemctl stop agentic-platform

# If running via Docker
docker stop agentic-platform --time 0

# If running directly — find and kill the process
pkill -f "uvicorn api.app:app"
```

### Option 2: Disable External Calls Only (SEV-3)

Revoke API keys to cut off external dependencies:

```bash
# Clear the Groq API key (stops all LLM inference)
unset GROQ_API_KEY

# Clear Tavily key (stops web search)
unset TAVILY_API_KEY

# Restart the server — it will return errors for agent endpoints
# but /health and /runs will still work
python main.py serve
```

### Option 3: Block at Network Level

```bash
# Block outgoing traffic to LLM provider
iptables -A OUTPUT -d api.groq.com -j DROP

# Block Tavily
iptables -A OUTPUT -d api.tavily.com -j DROP
```

## Post-Shutdown Checklist

- [ ] Notify stakeholders and incident commander
- [ ] Preserve logs for forensic analysis
- [ ] Identify root cause
- [ ] Fix the issue and validate in staging
- [ ] Re-enable using the rollback runbook if needed
- [ ] Conduct post-incident review within 48 hours

## Contacts

| Role | Contact |
|------|---------|
| Platform Owner | Platform team lead |
| Security | Security team |
| On-Call | Ops rotation |
