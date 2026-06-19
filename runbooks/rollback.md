# Rollback Procedure

## Purpose

This runbook describes how to roll back a bad deployment of the Agentic AI Platform to a known-good state.

## Pre-Requisites

- Access to the deployment server or container orchestration system
- Git access to the source repository
- Database backup from the previous release

## Rollback Steps

### 1. Identify the Issue

- Check application logs via `structlog` output or LangSmith traces
- Verify the failure using the health endpoint: `GET /health`
- Note the current deployed commit hash: `git rev-parse HEAD`

### 2. Stop the Running Service

```bash
# If running via systemd
sudo systemctl stop agentic-platform

# If running via Docker
docker stop agentic-platform

# If running directly
# Send SIGTERM to the uvicorn process
kill -TERM <PID>
```

### 3. Roll Back to Previous Version

```bash
# Identify the last known-good tag or commit
git log --oneline -5

# Checkout the previous release
git checkout <previous-tag-or-commit>

# Reinstall dependencies
pip install -r requirements.txt
```

### 4. Restore Database (if needed)

```bash
# SQLite: restore from backup
cp backups/agentic_platform.db.bak ./agentic_platform.db

# Verify database integrity
python -c "from database import init_db; import asyncio; asyncio.run(init_db())"
```

### 5. Restart the Service

```bash
python main.py serve
```

### 6. Verify Recovery

- Check health endpoint: `GET http://localhost:8000/health`
- Run a test workflow: `POST /run` with a simple query
- Monitor logs for 15 minutes for any errors

## Post-Rollback

- Create an incident report
- Identify root cause before re-deploying the fix
- Ensure CI/CD pipeline tests pass before next deployment
