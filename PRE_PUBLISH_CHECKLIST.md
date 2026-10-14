# Pre-publish checklist

Scope: reviewed source and Git index, not the ignored local workspace. This is a
portfolio repository, not a certified production deployment.

- [x] No secrets in reviewed public source/index.
- [x] Initial history availability checked: no Git history existed before local initialization.
- [x] .env and .env.* ignored; .env.example explicitly allowed.
- [x] .env.example contains dummy localhost values and fixture defaults only.
- [x] Frontend bundle contains no configured credentials.
- [x] Real listing downloads, local databases, logs, caches and installed dependencies ignored.
- [x] Published screenshots reviewed; third-party photo screenshots archived locally.
- [x] Fixture workflow works without external API keys.
- [x] Missing/failed live providers fail safely without fixture fallback.
- [x] Automated tests block external HTTP calls.
- [x] Backend tests pass (81 including the optional MCP group).
- [x] Python lint passes.
- [x] Frontend lint passes.
- [x] TypeScript check passes.
- [x] Frontend production build passes.
- [x] Deterministic evaluation passes (6/6; not model-quality evidence).
- [x] Server enforces persisted approval/ownership and payload/current-record checks.
- [x] Duplicate approval is idempotent; rejection does not execute.
- [x] n8n public export has no credentials or pinned data; separate human-decision entry point.
- [x] n8n flow was imported and locally tested; platform audit/retention limits documented.
- [x] Two read-only MCP tools and stdio protocol tested.
- [x] README claims separate verified, unverified and planned behavior.
- [x] Docker status is explicit: Desktop installed and Compose parsing verified; engine blocked on host services; DISM health repaired, SFC blocked on Windows pending repair restart; no runtime check.
- [x] Core dependency audit results recorded; optional n8n advisories disclosed.
- [x] MIT license and security policy included.
- [x] Final staged file list, whitespace and secret scan reviewed.

## Recheck immediately before committing

From the checkout root, with local fixture services available:

```powershell
backend\.venv\Scripts\python.exe tools\security_scan.py
git status --short
git diff --cached --check
git ls-files
```

From backend:

```powershell
uv sync --group mcp
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe ..\evals\run.py
```

From frontend:

```powershell
npm ci
npm run lint
npm run typecheck
npm run build
```

Do not use git add -f for ignored files. Inspect staged paths before creating the
commit. See GITHUB_METADATA.md for source-repository publication status. No public
application deployment is claimed.

## 2026-10-14 additions

- [x] Actual keyless Ollama runs preserved, including semantic failures and prior iterations.
- [x] Structured-output counts distinguished from model accuracy.
- [x] Synthetic rule diagnostic preserves three remaining deviations.
- [x] Demo GIF contains only synthetic records; captured fixture mode is labeled.
- [x] One-terminal launcher exercised with existing Windows prerequisites.
- [x] Local-model summaries excluded from task arguments; backend drafts retained.
- [x] REAL-* archive guard blocks non-fixture generation or embedding.
- [ ] Docker/native PostgreSQL build, readiness and concurrency verified.
