"""Build a small local review ZIP with an explicit source-file allowlist."""

import hashlib
import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "review-package"
TOP_FILES = {
    "README.md",
    "REVIEWER_GUIDE.md",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    ".gitattributes",
    "compose.yaml",
    "SECURITY.md",
    "LICENSE",
    "PRE_PUBLISH_CHECKLIST.md",
    "GITHUB_METADATA.md",
    "pytest.ini",
}
SOURCE_ROOTS = {
    "backend",
    "frontend",
    "tools/local-db",
    "data/company_docs",
    "data/fixtures",
    "examples/mcp",
    "n8n",
}
EXCLUDE_DIRS = {
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}
SOURCE_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".css",
    ".html",
    ".json",
    ".toml",
    ".ini",
    ".mako",
    ".mjs",
    ".lock",
    ".md",
}
EXTRA_FILES = {
    ".github/workflows/compose-check.yml",
    "tools/smoke_compose.py",
    "tools/start_demo.py",
    "tools/build_demo_gif.py",
    "evals/local_model.py",
    "evals/rule_robustness.py",
    "evals/rule_robustness_cases.jsonl",
    "docs/ARCHITECTURE.md",
    "docs/LOCAL_SETUP.md",
    "docs/demo/workflow.gif",
    "docs/demo/local-model.png",
    "docs/demo/capture.json",
    "docs/verification/LOCAL_MODEL_REVIEW.md",
    "docs/verification/local-model.json",
    "docs/verification/docker.json",
    "docs/verification/local-model-baseline.json",
    "docs/verification/local-model-v2.json",
    "docs/verification/rule-robustness-baseline.json",
    "docs/verification/rule-robustness.json",
    "evals/run.py",
    "evals/cases.jsonl",
    "tools/package_review.py",
    "docs/PLAN.md",
    "docs/MILESTONE-1.md",
    "docs/VEHICLE-DEMO.md",
    "docs/REAL-LISTING-TRIAL.md",
    "docs/screenshots/main-workflow.jpg",
    "docs/screenshots/approval.jpg",
    "docs/screenshots/audit-result.jpg",
    "docs/verification/summary.json",
    "docs/verification/n8n.json",
    "docs/verification/mcp.json",
    "docs/verification/fixture-evaluation.json",
    "docs/verification/security.json",
    "tools/security_scan.py",
    "tools/integration_env.py",
    "tools/n8n_local.py",
    "tools/prepare_n8n_local.py",
    "tools/setup_n8n_local.py",
    "tools/smoke_n8n.py",
    "tools/smoke_mcp.py",
    "tools/build_n8n_workflow.py",
    "evals/reports/latest.json",
}


def include(path):
    relative = path.relative_to(ROOT)
    name = relative.as_posix()
    if name in TOP_FILES or name in EXTRA_FILES:
        return True
    if any(part in EXCLUDE_DIRS for part in relative.parts):
        return False
    if path.name in {"Dockerfile", ".dockerignore"}:
        return relative.parts[0] in {"backend", "frontend"}
    return path.suffix in SOURCE_SUFFIXES and any(
        name.startswith(prefix + "/") for prefix in SOURCE_ROOTS
    )


def package():
    candidates = {ROOT / name for name in TOP_FILES | EXTRA_FILES}
    for source_root in SOURCE_ROOTS:
        for directory, subdirs, names in os.walk(ROOT / source_root, followlinks=False):
            subdirs[:] = [name for name in subdirs if name not in EXCLUDE_DIRS]
            candidates.update(Path(directory) / name for name in names)
    files = sorted(
        path for path in candidates if path.is_file() and not path.is_symlink() and include(path)
    )
    names = [path.relative_to(ROOT).as_posix() for path in files]
    if ".env" in names or any("real_listings/" in name for name in names):
        raise ValueError("A private local file entered the allowlist")
    OUTPUT.mkdir(exist_ok=True)
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "project": "Agentic Workflow Assistant",
        "runtime_mode": "fixture",
        "entry_point": "REVIEWER_GUIDE.md",
        "limits": [
            "Local model semantic errors documented; remote providers unverified",
            "External n8n platform audit/retention limitations",
            "No Docker runtime verification",
        ],
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in files
        ],
    }
    zip_path = OUTPUT / "agentic-workflow-assistant-review.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "agentic-workflow-assistant/" + path.relative_to(ROOT).as_posix())
        archive.writestr(
            "agentic-workflow-assistant/REVIEW_MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
        assert "agentic-workflow-assistant/REVIEWER_GUIDE.md" in archive.namelist()
        assert "agentic-workflow-assistant/backend/uv.lock" in archive.namelist()
        assert "agentic-workflow-assistant/frontend/package-lock.json" in archive.namelist()
        assert (
            "agentic-workflow-assistant/data/company_docs/demo-operations.md" in archive.namelist()
        )
        assert (
            "agentic-workflow-assistant/data/fixtures/vehicle_listings.json" in archive.namelist()
        )
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "zip": str(zip_path),
                "files": len(files),
                "bytes": zip_path.stat().st_size,
            }
        )
    )


if __name__ == "__main__":
    package()
