"""Publication scan. Findings show locations/categories, never matched values.

--workspace includes ignored project artifacts (not installed third-party code).
The normal scan uses Git's index plus non-ignored files and scans frontend dist
separately for credential leakage. This is a bounded heuristic, not certification.
"""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "provider-key": r"\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}|AIza[A-Za-z0-9_-]{30,})\b",
    "jwt": r"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b",
    "literal-bearer": r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}",
    "private-key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "machine-path": (
        r"(?:[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_. -]+[\\/]"
        r"|/(?:Users|home)/[A-Za-z0-9_.-]+/)"
    ),
    "private-network-url": (
        r"https?://(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+"
        r"|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)"
    ),
    "credential-assignment": (
        r"(?i)(?:api[_-]?key|password|secret|token)[\"']?"
        r"\s*[=:]\s*[\"']?([A-Za-z0-9+/=_-]{24,})"
    ),
}
VENDOR = {"node_modules", ".venv", "venv", ".git", "uv-cache", "npm-cache", ".cache"}
TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".html",
    ".css",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".lock",
    ".log",
    ".env",
    ".example",
    ".ps1",
}


def git_paths():
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return sorted({ROOT / name for name in result.stdout.decode().split("\0") if name})


def workspace_paths():
    files = []
    for directory, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in VENDOR]
        files.extend(Path(directory) / name for name in names)
    return files


def harmless(value):
    lower = value.lower()
    return any(
        mark in lower for mark in ("change-me", "placeholder", "replace-with", "test-only", "your-")
    )


def scan(paths, scope):
    findings = []
    count = 0
    for path in paths:
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {
            ".env",
            "Dockerfile",
            ".gitignore",
            ".dockerignore",
        }:
            continue
        count += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for category, expression in PATTERNS.items():
            for match in re.finditer(expression, text):
                if category == "credential-assignment" and harmless(match.group(1)):
                    continue
                findings.append(
                    {
                        "file": path.relative_to(ROOT).as_posix(),
                        "line": text.count("\n", 0, match.start()) + 1,
                        "category": category,
                        "scope": scope,
                    }
                )
    return count, findings


def bundle_leaks():
    # Compare configured values without logging or exporting them.
    env = ROOT / ".env"
    values = []
    if env.exists():
        for line in env.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and ("KEY" in key or "TOKEN" in key or "SECRET" in key) and value.strip():
                values.append(value.strip().strip("\"'"))
    leaked = []
    for path in (ROOT / "frontend/dist").rglob("*"):
        if path.is_file() and path.suffix in {".js", ".html", ".css", ".map"}:
            body = path.read_text(errors="replace")
            if any(value in body for value in values):
                leaked.append(
                    {
                        "file": path.relative_to(ROOT).as_posix(),
                        "category": "configured-secret-in-bundle",
                        "scope": "frontend-bundle",
                    }
                )
    return leaked


def index_findings():
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    findings = []
    for name in result.stdout.decode().split("\0"):
        if not name:
            continue
        relative = Path(name)
        forbidden = any(
            part in {"node_modules", ".venv", ".local", ".tmp", "logs", "real_listings"}
            for part in relative.parts
        )
        forbidden |= relative.name.startswith(".env") and relative.name != ".env.example"
        forbidden |= relative.suffix in {
            ".pem",
            ".key",
            ".p12",
            ".pfx",
            ".db",
            ".sqlite",
            ".sqlite3",
        }
        if forbidden:
            findings.append(
                {"file": name, "category": "sensitive-artifact-tracked", "scope": "git-index"}
            )
        if relative.suffix not in TEXT_SUFFIXES and relative.name not in {
            ".env.example",
            "Dockerfile",
        }:
            continue
        staged = subprocess.run(
            ["git", "show", ":" + name], cwd=ROOT, capture_output=True, check=True
        ).stdout.decode(errors="replace")
        for category, expression in PATTERNS.items():
            for match in re.finditer(expression, staged):
                if category == "credential-assignment" and harmless(match.group(1)):
                    continue
                findings.append(
                    {
                        "file": name,
                        "line": staged.count("\n", 0, match.start()) + 1,
                        "category": category,
                        "scope": "git-index",
                    }
                )
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", action="store_true")
    args = parser.parse_args()
    count, findings = scan(git_paths(), "publication")
    findings.extend(bundle_leaks())
    findings.extend(index_findings())
    local_count, local_findings = (
        scan(workspace_paths(), "local-artifact") if args.workspace else (0, [])
    )
    history = subprocess.run(
        ["git", "rev-list", "--all"], cwd=ROOT, capture_output=True, check=True
    )
    report = {
        "git_history_commits_available": len(history.stdout.splitlines()),
        "public_text_files_scanned": count,
        "public_findings": findings,
        "owned_workspace_text_files_scanned": local_count,
        "local_artifact_findings": local_findings,
        "boundary": "Installed dependencies and package caches are not project source; "
        "use dependency audits separately.",
    }
    print(json.dumps(report, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
