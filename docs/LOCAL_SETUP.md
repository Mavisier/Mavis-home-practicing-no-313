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

## Docker target — runtime unverified

Docker packages the database, backend and frontend into containers with their own
runtimes. Compose describes how to build/start them together, avoiding manual
installation of each app dependency. It needs a working Docker engine.

On 2026-10-14, a valid Docker Inc signed Desktop 4.95.0 installer completed
per-user installation after Virtual Machine Platform was enabled and the user
restarted Windows. Docker CLI 29.8.2 and Compose 5.6.0 are installed. The actual
`docker compose config --quiet` check passed using the ignored synthetic demo
configuration. This verifies configuration parsing only, not container runtime.

The engine could not start: Windows reported virtualization unavailable despite
Virtual Machine Platform being Enabled and the hypervisor being detected. The
`vmcompute`/`hns` services and `vmcompute.exe` were absent. An elevated check
confirmed the state. Microsoft-Hyper-V-Services was enabled with dependencies and
`-NoRestart`; Windows returned `RestartNeeded=true`. No automatic reboot occurred.
After the user restarted again, the services/executable remained absent despite
Enabled feature states. An elevated health check reported Repairable. DISM
RestoreHealth completed successfully with Healthy status and no automatic reboot.
A subsequent SFC scan exited with code 1 before scanning: Windows reported a
pending system repair that requires restart. Runtime/native PostgreSQL remain
unverified. Health repair does not prove the Docker root cause is resolved.
See [bounded status report](verification/docker.json).

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
the verified local-model path is the native launcher. Validate container readiness,
approvals and concurrency before marking Docker verified. OpenAI/Anthropic remain
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
