# Security policy and demo boundary

This is a localhost portfolio application, not production authentication or a
publicly deployed service. Use fixture mode with synthetic records for review.

## Secrets and publication

Secrets/configuration are loaded from environment variables or the ignored local
`.env`. Never commit `.env`, certificates, private keys, logs, database files,
`.local`, `.tmp`, dependency installations, real listing downloads or third-party
photo screenshots. `.env.example` contains explicit dummy development values.
Fixture mode needs no external API key. Optional remote providers fail explicitly
when a key/model is missing and do not silently fall back to fixture mode.

Frontend bundles must contain no configured API key or demo credential. The local
Vite/Nginx proxy supplies demo headers server-side. Two demo roles use separate
values, but one local operator can use both; this is not SSO or production role
separation. Ports are bound to loopback in the supplied configuration.

## Controls implemented

- Pydantic validates bounded identifiers, requests, findings and explanations.
- Tool names/targets are allowlisted; no model-selected SQL, shell or URL tool.
- Queries use SQLAlchemy parameters, never interpolated SQL.
- Backend ownership checks apply to reads, edits, actions and sample files.
- Consequential local tasks require persisted server-side approval state.
- Approval verifies the stored payload hash and current vehicle snapshot.
- Row locks and a unique task/action relationship prevent duplicate execution.
- HTML is escaped and script execution is denied in served offline snapshots.
- File paths are validated after resolution, including symlink escapes.
- Provider errors exposed to users are sanitized; auth headers are not logged by
  the application's audit/event code. Tests block external HTTP requests.
- Public-input trial imports run in fixture mode and do not send data to a provider.

## n8n boundary

The public workflow export has no credential objects or values. Native header-auth
credentials are assigned to a separate ignored local copy. Review and human-decision
webhooks use different credentials. No review branch automatically approves.

n8n is an external platform. The locally tested npm runtime reported upstream
dependency advisories, including critical severity, and is excluded from this
repository. Its engine can retain trigger headers in private execution storage
even when execution-payload saving is configured off. Local verification keys
were rotated and those generated test records were removed. Do not share that
runtime/database or expose it publicly. Review current vendor advisories and
platform retention/redaction settings before using it with real credentials/data.
The application is fully usable without n8n.

## Reporting

For a public repository, use GitHub's private vulnerability reporting when enabled
or contact the repository owner privately. Never post credentials, private data
or exploit payloads containing real secrets in a public issue. Until a repository
owner/contact is configured, share a sanitized report with the project owner
through the existing private communication channel. No invented contact address
is supplied here.

## Known limitations

No production identity provider, rate limiting, cloud deployment, tenant isolation
or production observability claim is made. Local Ollama planning/summaries and neural embeddings were exercised, with known
semantic errors. Generated local summaries are excluded from task arguments;
questions/drafts are backend-generated. Lexical guards do not establish truth.
OpenAI/Anthropic and OpenAI embeddings remain unverified. Docker/native PostgreSQL
were exercised in fixture mode on Linux CI; this Windows engine remains blocked. Image damage/OCR analysis is not implemented. Fixture
evaluation measures contracts and safety behavior, not real-world model quality.
The heuristic secret scanner is a publication aid, not a security certification.

## Keyless local model

Ollama requests use an allowlisted local origin and explicit local model. Proxy
inheritance is disabled and no provider credential is attached. Archived REAL-*
records are blocked unless both generation and embedding providers are fixture.
Do not expose the local Ollama server publicly. Model summaries can still invent
facts; inspect typed findings and sources before approval. Audit logs contain
request/source/model text and require a retention policy for real deployments.

## CI boundary

The Compose workflow uses a standard GitHub-hosted Linux runner, synthetic fixtures
and dummy demo credentials. It requests only contents:read, pins actions by commit,
does not persist checkout credentials and uses no repository/provider secrets.
It executes tests and local task approvals, not a deployment or real communications.
The concurrency smoke check creates/removes only its own synthetic record/runs.
Evidence artifacts expire after seven days; a bounded report and the public run link
are preserved in docs/verification/compose-ci.json. Passing CI is not a certification.
