"""Local integration environment. Runtime credentials are ignored, never printed."""

import json
import os
import secrets
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def environment():
    config = dotenv_values(ROOT / ".env")
    directory = ROOT / ".local/integrations"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "keys.json"
    if path.exists():
        keys = json.loads(path.read_text())
    else:
        keys = {
            name: secrets.token_hex(32)
            for name in (
                "N8N_REVIEW_WEBHOOK_TOKEN",
                "N8N_DECISION_WEBHOOK_TOKEN",
                "N8N_ENCRYPTION_KEY",
            )
        }
        path.write_text(json.dumps(keys), encoding="utf-8")
    env = dict(os.environ)
    env.update(
        {
            "ASSISTANT_BASE_URL": "http://127.0.0.1:8000",
            "ASSISTANT_DEMO_REQUESTER_TOKEN": config["DEMO_REQUESTER_TOKEN"],
            "ASSISTANT_DEMO_APPROVER_TOKEN": config["DEMO_APPROVER_TOKEN"],
            "N8N_USER_FOLDER": str(ROOT / ".local/n8n"),
            "N8N_HOST": "127.0.0.1",
            "N8N_LISTEN_ADDRESS": "127.0.0.1",
            "N8N_PORT": "5678",
            "N8N_PROTOCOL": "http",
            "N8N_SECURE_COOKIE": "false",
            "N8N_BLOCK_ENV_ACCESS_IN_NODE": "false",
            "N8N_PAYLOAD_SIZE_MAX": "1",
            "N8N_DIAGNOSTICS_ENABLED": "false",
            "N8N_VERSION_NOTIFICATIONS_ENABLED": "false",
            "N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS": "true",
            "N8N_LOG_LEVEL": "warn",
            "N8N_UNVERIFIED_PACKAGES_ENABLED": "false",
            "DB_TYPE": "sqlite",
            "TEMP": str(ROOT / ".tmp"),
            "TMP": str(ROOT / ".tmp"),
            **keys,
        }
    )
    return env


def n8n_command(*arguments):
    return ["node", str(ROOT / ".local/n8n-runtime/node_modules/n8n/bin/n8n"), *arguments]
