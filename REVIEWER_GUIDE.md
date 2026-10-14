# Reviewer guide

This is a localhost portfolio prototype with fixture defaults. Start with README.md;
the status table separates local verification, unverified live paths and future work.

## Five-minute review

1. Read the README overview, architecture and limitations.
2. Run `python tools/start_demo.py --setup`; see docs/LOCAL_SETUP.md for prerequisites.
3. Open the UI and select Kurgusal demo örnekleri → Beyan çelişkisi.
4. Run review and expand a retrieved source.
5. Inspect the finding and unsent seller-message draft.
6. Confirm the proposed action is pending; no task has executed.
7. Approve or reject; inspect persisted status, task queue and audit history.
8. Repeated approval must not create a second task.
9. Optionally use n8n/README.md for the same flow through separate review/decision
   webhooks; the core app does not depend on n8n.
10. Run tests and evaluation; optionally use the two read-only MCP tools.

The clean package contains only synthetic records and safe screenshots. A separate
local trial used public listings/photos; raw downloads are not published.

## Important code

- backend/app/services/review.py — bounded workflow, sources, structured result,
  immutable proposal and event log.
- backend/app/api/reviews.py — ownership, approval authority, payload/current-record
  checks, transactions, idempotency and safe sample-file serving.
- backend/app/services/providers.py, local_model.py and knowledge.py — fixture/live split,
  allowlisted planning, atomic ingestion and embedding-space isolation.
- backend/app/schemas.py — input/output contracts and limits.
- backend/tests — safety, provider failures, retrieval, n8n graph and MCP contracts.
- n8n/agentic-review-workflow.json — one credential-free orchestration export.
- examples/mcp/server.py — two GET-only tools.

## Evidence

81 backend tests and six deterministic evaluation cases were locally verified on 2026-10-14.
Frontend lint/typecheck/build passed. n8n import and eight flow checks passed;
MCP stdio initialization and both tools were exercised. Verification summaries
are in docs/verification. Core dependency audits found no known advisories at the
audit date.

Actual local Ollama planning/summaries and neural embeddings were exercised on 30 synthetic cases.
See docs/verification/LOCAL_MODEL_REVIEW.md for raw evidence and semantic errors.
Twenty cases used generated summaries; ten empty results used approved wording
after real model planning. Seller drafts/questions are backend-generated.
Docker Compose/native PostgreSQL passed on Linux CI: 81 tests, six fixture cases,
and eight concurrent approvals producing one task/execution event. See
docs/verification/compose-ci.json and the linked public run. Windows Docker
readiness and OpenAI/Anthropic remain unverified. The
optional n8n npm runtime has upstream dependency/retention limitations and is
excluded from the repository. Read SECURITY.md before treating a demo as a
deployment starting point. Passing fixture tests does not prove AI accuracy,
production scale or business impact.

## AI review prompt

Review this extracted project. Start with README.md and REVIEWER_GUIDE.md. Distinguish
verified fixture behavior and actual local-model evidence from unverified paths and planned work. Read the published semantic failures; schema validity is not accuracy. Inspect tool
allowlists, retrieval attribution, bounded schemas, approval authority, ownership,
payload/current-record checks, idempotency, error handling and tests. Use fixture
mode only; do not enable paid calls, fetch public listings, publish or message users.
If you can execute code, reproduce the documented checks and report your environment.
If you cannot, label the result as a static review. Report actionable findings with
file/line, severity and evidence. Assess relevance to Forward Deployed AI engineering,
without inferring model quality or production readiness from fixture checks.

A reviewer/AI needs the source ZIP, repository access or a local checkout. The
operator's localhost URL and screenshots do not grant source-code access.

## Candidate presentation

Describe the project as an AI-assisted portfolio prototype. Be ready to explain
why the backend controls authority, where the human gate is, what the tests prove
and how company-specific data/policies would enter a measured pilot. Do not claim
years of experience, customers, deployment or measured business impact from this demo.

## Free local-model review

Optional: keep Ollama running, download qwen2.5:7b and nomic-embed-text:v1.5, stop
the fixture demo, and use `python tools/start_demo.py --provider ollama --neural`.
The standard review prompt above keeps fixture mode unless the reviewer explicitly
chooses this keyless path. Never enable paid calls automatically.
