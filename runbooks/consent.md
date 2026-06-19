# Consent Capture Procedure

## DPDP S.6/S.7 Compliance

This document outlines how the Agentic AI Platform captures, records, and manages user consent in compliance with the India Digital Personal Data Protection Act, 2023 (DPDP Act).

## Consent Model

### Data Processed

The platform processes the following personal data:

| Data Type | Purpose | Legal Basis |
|-----------|---------|-------------|
| User name | Personalization of agent responses | Consent (DPDP S.6) |
| User email | Communication and account identification | Consent (DPDP S.6) |
| Resume text | Career guidance analysis (Career Agent) | Explicit consent (DPDP S.7) |
| Phone number | Contact information for support | Consent (DPDP S.6) |
| Chat queries | Agent processing and response generation | Consent (DPDP S.6) |

### Consent Capture Flow

1. **First Interaction**: Users are presented with a clear, plain-language consent notice before submitting any data to the platform
2. **Explicit Consent**: For sensitive data like resume text, explicit opt-in consent is captured via a dedicated consent checkbox
3. **Consent Recording**: Consent is recorded in the platform database with:
   - User identifier
   - Timestamp of consent
   - Scope of consent (which data types)
   - Version of the privacy notice shown
4. **Granular Control**: Users can provide consent separately for:
   - Research queries (web search data)
   - Career analysis (resume/profile data)
   - Code review (code snippets)

### Consent Withdrawal

Users can withdraw consent at any time through the following mechanism:

1. Navigate to the platform settings or contact the platform administrator
2. Select the data categories to withdraw consent for
3. Upon withdrawal:
   - The platform stops processing the specified data types within **24 hours**
   - Associated data is queued for deletion per the [Data Retention Policy](./data-retention.md)
   - Deletion is completed within **72 hours** of withdrawal
4. Withdrawal is recorded with a timestamp in the audit log

### Consent for Minors (DPDP S.9)

- The platform does not knowingly process data of minors (under 18)
- Age verification is required during onboarding
- If minor data is detected, processing is halted and data is deleted

## Audit Trail

All consent events are logged with:
- Event type (grant / withdraw / modify)
- Timestamp (UTC)
- User identifier (hashed)
- IP address (hashed for privacy)
- Consent scope
