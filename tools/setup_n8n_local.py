"""Optional verification runtime installed under ignored .local, never vendored.

Review n8n's own advisories before deployment. This helper pins the version used
by the local integration trial; it is not a claim of production security.
"""

import json
import os
import subprocess

from integration_env import ROOT

if __name__ == "__main__":
    target = ROOT / ".local/n8n-runtime"
    target.mkdir(parents=True, exist_ok=True)
    (target / "package.json").write_text(
        json.dumps(
            {"name": "local-n8n-verification", "private": True, "dependencies": {"n8n": "2.42.7"}}
        ),
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "TEMP": str(ROOT / ".tmp"),
        "TMP": str(ROOT / ".tmp"),
        "npm_config_cache": str(ROOT / ".tmp/npm-cache"),
    }
    command = "npm.cmd" if os.name == "nt" else "npm"
    subprocess.run([command, "install", "--no-fund", "--no-audit"], cwd=target, env=env, check=True)
