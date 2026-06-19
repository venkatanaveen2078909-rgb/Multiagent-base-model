# Data Retention Policy

## DPDP S.8(7) Compliance

This document defines the data retention periods for all personal and operational data processed by the Agentic AI Platform, in compliance with the India DPDP Act 2023, Section 8(7).

## Retention Schedule

| Data Type | Retention Period | Auto-Delete | Storage Location | Justification |
|-----------|-----------------|-------------|------------------|---------------|
| Chat queries (user_input) | 90 days | Yes (TTL) | SQLite/PostgreSQL | Operational — debugging and quality improvement |
| Agent responses (result) | 90 days | Yes (TTL) | SQLite/PostgreSQL | Operational — tied to chat queries |
| Evaluation scores | 90 days | Yes (TTL) | SQLite/PostgreSQL | Quality monitoring |
| Resume text | 30 days | Yes (TTL) | SQLite/PostgreSQL | Short retention — sensitive personal data |
| User name / email | Until erasure request | On request | SQLite/PostgreSQL | Account identification |
| Phone number | Until erasure request | On request | SQLite/PostgreSQL | Contact purposes |
| LangSmith traces | 60 days | Yes (TTL) | LangSmith Cloud | Observability and debugging |
| API access logs | 180 days | Yes (TTL) | Server filesystem | Security audit trail |
| Consent records | 7 years | No (legal requirement) | SQLite/PostgreSQL | Regulatory compliance |
| Incident reports | 7 years | No (legal requirement) | Document storage | Regulatory compliance |

## Retention Rules

### Principle of Data Minimisation

- Data is retained only for the minimum period necessary to fulfil its stated purpose
- Once the retention period expires, data is automatically deleted via scheduled cleanup jobs
- No personal data is retained indefinitely without legal justification

### Automated Cleanup

The platform runs automated cleanup processes:

```sql
-- Delete agent runs older than 90 days
DELETE FROM agent_runs WHERE created_at < datetime('now', '-90 days');

-- Delete evaluation records older than 90 days
DELETE FROM eval_records WHERE created_at < datetime('now', '-90 days');

-- Delete resume-related data older than 30 days
DELETE FROM agent_runs
WHERE agent_name = 'career_agent'
AND created_at < datetime('now', '-30 days');
```

### Manual Override

- Data subjects can request early deletion at any time (see [Erasure Procedure](./erasure-procedure.md))
- Manual deletion requests are processed within **72 hours**

## Data Backup Retention

| Backup Type | Retention | Encryption |
|-------------|-----------|------------|
| Daily database backup | 30 days | AES-256 at rest |
| Weekly snapshot | 90 days | AES-256 at rest |

## Review Schedule

This retention policy is reviewed:
- **Annually** as part of the compliance audit cycle
- **On any change** to data processing activities
- **On regulatory updates** to the DPDP Act or related guidelines
