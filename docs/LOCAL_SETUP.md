# Local setup

Run commands from the checkout root. Prerequisites: Python 3.12–3.14, Node.js 24
with npm, and uv. Windows was tested with installed prerequisites; Linux/macOS and
a fresh machine were not tested. App databases, logs and caches stay inside this
checkout and are ignored. Ollama uses normal OS application/model storage.

## One terminal

```powershell
python tools/start_demo.py --setup
```

This installs locked dependencies, copies `.env.example` only if `.env` is absent,
starts PGlite, applies migrations, seeds synthetic records, ingests knowledge, and
starts FastAPI and Vite. Later runs:

```powershell
python tools/start_demo.py
```

UI: http://127.0.0.1:5173; API: http://127.0.0.1:8000/docs. These are local URLs,
not a hosted deployment. Ctrl+C stops only owned processes. Occupied ports are
rejected. Logs: `.local/demo-logs`. The launcher explicitly selects fixture mode
and the local database even if the ignored `.env` has different provider settings;
it never enables paid calls. Dependency installation needs network access.

PGlite is PostgreSQL/Wasm with pgvector on port 55432. The helper uses one connection;
it is not native PostgreSQL concurrency evidence.

## Actual local model, no API key

Install [Ollama](https://ollama.com/download/windows) and keep its local server
running. Tested: Ollama 0.40.3, qwen2.5:7b (Q4_K_M, about 4.7 GB) and
nomic-embed-text:v1.5 (about 274 MB, 768 dimensions). Download once:

```powershell
ollama pull qwen2.5:7b
ollama pull nomic-embed-text:v1.5
python tools/start_demo.py --provider ollama --neural
```

Stop the fixture demo first. The launcher re-ingests four documents into the
selected embedding space; switching back re-ingests fixture vectors. It does not
change stored `.env` or use API keys. Native `/api/chat` supplies tool calls and
structured summaries; `/api/embed` supplies neural vectors. Requests use a local
origin with proxy inheritance disabled; remote origins/cloud tags are rejected.
There are no paid API calls; hardware/electricity costs still exist.

Actual runs used 31 GB RAM and a 12 GB GPU. Memory/performance vary; the adapter
timeout is 120 seconds. Smaller models were not validated. Read the
[observed quality errors](verification/LOCAL_MODEL_REVIEW.md).
Official API references: [tools](https://docs.ollama.com/capabilities/tool-calling),
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
[embeddings](https://docs.ollama.com/api/embed).

## Reproduce checks

Keep the **fixture** launcher running for tests and six workflow cases:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
backend/.venv/Scripts/ruff.exe check backend tools evals examples --config backend/pyproject.toml
backend/.venv/Scripts/python.exe evals/run.py
backend/.venv/Scripts/python.exe evals/rule_robustness.py
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

On Unix use `.venv/bin/python` and `.venv/bin/ruff`. From `backend`, activate the
venv and run `python -m alembic check`. The rule diagnostic reports three deviations;
it is not a passing accuracy test. Unit tests mock provider HTTP and block external
requests; they do not download models.

For an **actual** model evaluation, keep the Ollama/neural launcher running instead:

```powershell
backend/.venv/Scripts/python.exe evals/local_model.py
```

It runs `process_review` on 30 temporary synthetic records, writes ignored
`evals/reports/local-model.json`, and removes its own temporary database records.
It does not test HTTP transport, native concurrency, real approval identities or
domain-expert semantic accuracy. Review failed/incorrect outputs before publishing.

## Docker Compose — verified on Linux CI

Docker packages the database, backend and frontend into containers. Compose builds
and starts them together. It needs a working local Docker engine.

On 2026-10-14, the same Compose configuration was built and started on a standard
GitHub-hosted Ubuntu 24.04 runner with native PostgreSQL 17.11/pgvector. All 81
backend tests, six fixture evaluations and the HTTP concurrency smoke check passed.
Eight simultaneous approvals created one task and one execution event. The Nginx
frontend/proxy, requester/reviewer gates and rejection were checked over HTTP.
This is fixture/synthetic evidence, not live-model, load/scale or real identity proof.
[Passing run](https://github.com/Mavisier/Mavis-home-practicing-no-313/actions/runs/38612421807)
· [saved report](verification/compose-ci.json)

The workflow `.github/workflows/compose-check.yml` runs on relevant main-branch
pushes or manual Actions dispatch. It builds the existing Dockerfiles, runs locked
Python dependencies with the optional MCP group and saves a seven-day artifact.
It uses dummy demo credentials and no repository/provider secrets. Standard hosted
runners are free for public repositories per
[GitHub's documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job).

The local Windows host is a separate unresolved issue. Docker Desktop 4.95.0 was
installed and Compose 5.6.0 parsing passed. Windows feature flags are Enabled but
Host Compute services/executable remain absent. DISM repaired the component store
from Repairable to Healthy. Actual restarts did not apply the pending Windows
installation queue; SFC still refuses to start due to a pending system repair.
No pending files or boot registry values were edited manually. This Linux run does
not prove this Windows engine is ready. [Local status](verification/docker.json)

For a different Windows machine, follow the official
[Docker installation instructions](https://docs.docker.com/desktop/setup/install/windows-install/)
and [WSL setup](https://learn.microsoft.com/en-us/windows/wsl/install).
Check current license terms for your use case. After the engine is ready, copy
`.env.example` to `.env` if absent and stop the native launcher to release ports:

```powershell
docker compose up --build -d
docker compose down
```

Compose overrides the database URL for native PostgreSQL. It does not start Ollama;
the verified local-model path is the native launcher. The CI validates container
readiness, approvals and small concurrency in fixture mode on Linux. OpenAI/Anthropic remain
implemented but unverified; this free demo does not enable them. Optional setup:
[n8n](../n8n/README.md), [MCP](../examples/mcp/README.md).

For validation without forwarding your ordinary `.env` (which may contain provider
keys), use an ignored copy of the synthetic defaults. Compose's `DEMO_ENV_FILE`
selects the backend/migration env file; `--env-file` selects interpolation values:

```powershell
Copy-Item .env.example .local/docker-verification.env
$env:DEMO_ENV_FILE = '.local/docker-verification.env'
docker compose --env-file .local/docker-verification.env config --quiet
docker compose --env-file .local/docker-verification.env up --build -d
```

The default remains `.env`. Never print expanded configuration with real secrets
or commit local env files. Clearing `DEMO_ENV_FILE` restores the normal file.

After Compose is ready, reproduce the additional check with the host backend venv.
Set `DATABASE_URL` to the native Compose socket on port 5433 and fixture providers;
use the same requester/reviewer values as the selected demo env file. The CI's
verification env uses an eight-connection pool. Then run:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://workflow:workflow@127.0.0.1:5433/workflow'
$env:LLM_PROVIDER = 'fixture'
$env:EMBEDDING_PROVIDER = 'fixture'
backend/.venv/Scripts/python.exe tools/smoke_compose.py
```

The script checks the local fixture configuration before creating a temporary
synthetic record, tests eight parallel approvals and removes its own records.
It writes ignored `.local/compose-verification.json`. Do not run it against a real
operational database. In Linux, use `backend/.venv/bin/python`.
