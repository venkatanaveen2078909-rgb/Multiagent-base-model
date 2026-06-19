# Right-to-Erasure Procedure

## DPDP S.11 Compliance

This document describes the process for handling data erasure requests (Right to Erasure) under the India Digital Personal Data Protection Act, 2023, Section 11.

## Scope

This procedure applies to all personal data processed by the Agentic AI Platform, including:

- User names and email addresses
- Phone numbers
- Resume text submitted to the Career Agent
- Chat queries and agent responses
- Evaluation records
- LangSmith observability traces

## Erasure Request Process

### Step 1: Receive Request

Erasure requests can be submitted through:
- Platform settings interface (self-service)
- Email to the designated Data Protection Officer
- Written request via registered post

**SLA**: Acknowledge receipt within **24 hours**

### Step 2: Verify Identity

Before processing any erasure request:
1. Verify the requester's identity using their registered email
2. Confirm the scope of data to be erased
3. Document the verification in the audit log

### Step 3: Execute Erasure

**Timeline**: Complete erasure within **72 hours** of verified request

#### 3a. Database Records

```sql
-- Delete all agent runs for the user
DELETE FROM agent_runs WHERE user_id = '<user_id>';

-- Delete all evaluation records linked to the user's runs
DELETE FROM eval_records
WHERE agent_run_id IN (
    SELECT id FROM agent_runs WHERE user_id = '<user_id>'
);

-- Delete user account record
DELETE FROM users WHERE id = '<user_id>';
```

#### 3b. LangSmith Traces

- Use the LangSmith API to delete all traces associated with the user's sessions
- Endpoint: `DELETE /api/v1/runs` with session filter

#### 3c. Backup Data

- Mark the user's data for exclusion in the next backup cycle
- Previous backups containing the user's data will age out per the retention schedule (max 90 days)

#### 3d. Log Files

- Structured logs (`structlog`) are rotated every 30 days
- User-identifiable content in logs is hashed, not stored in plaintext

### Step 4: Confirm Erasure

1. Run a verification query to confirm no records remain:
   ```sql
   SELECT COUNT(*) FROM agent_runs WHERE user_id = '<user_id>';
   -- Expected: 0
   ```
2. Send confirmation to the requester within **72 hours**
3. Record the completion in the erasure audit log

## Exceptions

Data may be retained despite an erasure request if required by law:
- Consent audit records (7-year legal retention)
- Data subject to active legal proceedings
- Data required for tax or financial compliance

The requester will be informed of any exceptions with legal justification.

## Audit Log

All erasure events are recorded:

| Field | Description |
|-------|-------------|
| Request ID | Unique identifier for the erasure request |
| Requester | Hashed user identifier |
| Request date | ISO 8601 timestamp |
| Verification date | When identity was verified |
| Completion date | When erasure was completed |
| Scope | Data categories erased |
| Exceptions | Any data retained with justification |
| Processed by | Operator identifier |

## Tools Supporting Erasure

The platform provides the following tools to support the erasure process:

- `delete_account` — Available as a destructive tool in the agent capabilities
- Database admin scripts in `database/` for bulk operations
- LangSmith API integration for trace deletion

## Review

This procedure is reviewed:
- Annually during the compliance audit
- After any erasure request to identify process improvements
- Upon updates to DPDP Act guidelines
