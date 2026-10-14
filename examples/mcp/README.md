# Read-only MCP example

Two tools expose existing persisted reviews through the local FastAPI API:
`get_listing_analysis(run_id)` and `get_review_status(run_id)`.

They perform GET requests only. There is no approval, rejection, execution,
arbitrary URL, shell or SQL tool. UUID inputs and the fixed local backend origin
are validated; the backend applies requester ownership checks. Tool errors do not
include authentication headers or connection details.

Install the optional group and start the backend as documented in the root README:

```powershell
uv sync --directory backend --group mcp
backend\.venv\Scripts\python.exe examples\mcp\server.py
```

The server uses stdio; connect a stdio-capable MCP client to this executable/script.
Use paths appropriate to your checkout in the client's configuration; do not
commit a machine-specific client config. Demo credentials stay in the ignored
root `.env`. `ASSISTANT_BASE_URL` defaults to `http://127.0.0.1:8000`; only local
HTTP origins (`localhost`, `127.0.0.1`, or the Compose `backend` host) are accepted.

Create a fixture review in the UI, copy its run UUID from the audit/API response,
and call either tool. Reading it must not create or approve any task.

This is an optional local integration, not a hosted MCP platform. The core UI and
backend do not need the MCP dependency. SDK: [official Python SDK](https://github.com/modelcontextprotocol/python-sdk).
