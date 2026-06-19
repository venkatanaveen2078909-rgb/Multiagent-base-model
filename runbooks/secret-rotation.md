# Secret Rotation Procedure

## Purpose

This runbook describes how to rotate API keys and secrets used by the Agentic AI Platform to maintain security hygiene and respond to key compromise events.

## Secrets Inventory

| Secret | Environment Variable | Provider | Rotation Frequency |
|--------|---------------------|----------|-------------------|
| Groq API Key | `GROQ_API_KEY` | [Groq Console](https://console.groq.com) | Every 90 days |
| Tavily API Key | `TAVILY_API_KEY` | [Tavily Dashboard](https://tavily.com) | Every 90 days |
| LangSmith API Key | `LANGSMITH_API_KEY` | [LangSmith](https://smith.langchain.com) | Every 90 days |
| Application Secret | `SECRET_KEY` | Self-generated | Every 90 days |
| Agent API Token | `AGENT_API_TOKEN` | Self-generated | Every 90 days |

## Rotation Procedure

### Step 1: Generate New Keys

1. **Groq**: Go to https://console.groq.com → API Keys → Create New Key
2. **Tavily**: Go to https://tavily.com → Dashboard → API Keys → Regenerate
3. **LangSmith**: Go to https://smith.langchain.com → Settings → API Keys → Create
4. **SECRET_KEY**: Generate a new random secret:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

### Step 2: Update the `.env` File

```bash
# Edit .env with the new keys
# IMPORTANT: Do NOT commit .env to version control

GROQ_API_KEY=<new-groq-key>
TAVILY_API_KEY=<new-tavily-key>
LANGSMITH_API_KEY=<new-langsmith-key>
SECRET_KEY=<new-secret-key>
```

### Step 3: Restart the Service

```bash
# Stop and restart to pick up new environment variables
python main.py serve
```

### Step 4: Verify

```bash
# Check health endpoint
curl http://localhost:8000/health

# Verify response shows:
# "groq_configured": true
# "tavily_configured": true

# Run a test query
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Test query after key rotation"}'
```

### Step 5: Revoke Old Keys

- Go to each provider's dashboard and **revoke/delete** the old key
- Verify the old key no longer works

## Emergency Key Rotation (Compromise Detected)

If a key is suspected to be compromised:

1. **Immediately revoke** the old key at the provider dashboard
2. Generate a new key
3. Update `.env` and restart
4. Audit logs for unauthorized usage during the exposure window
5. File an incident report
