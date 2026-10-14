"""Start fixture or an explicitly selected keyless local Ollama demo."""

import argparse
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def open_port(port):
    with socket.socket() as connection:
        connection.settimeout(0.2)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def wait_for_port(port, child, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError("A demo process stopped; inspect .local/demo-logs.")
        if open_port(port):
            return
        time.sleep(0.25)
    raise RuntimeError(f"Local port {port} did not become ready.")


def wait_for_api(child, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError("Backend stopped; inspect .local/demo-logs.")
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=2):
                return
        except (OSError, urllib.error.URLError):
            time.sleep(0.4)
    raise RuntimeError("Backend readiness timed out.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--setup", action="store_true", help="Install locked dependencies first (network required)."
    )
    parser.add_argument("--provider", choices=["fixture", "ollama"], default="fixture")
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--neural", action="store_true", help="Use local Ollama neural embeddings.")
    args = parser.parse_args()
    if args.neural and args.provider != "ollama":
        raise SystemExit("--neural requires --provider ollama.")
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required; see README prerequisites.")
    env = dict(os.environ)
    env.update(LLM_PROVIDER="fixture", EMBEDDING_PROVIDER="fixture", LLM_MODEL="")
    if args.provider == "ollama":
        if "cloud" in args.model.casefold():
            raise SystemExit("This launcher supports local models only.")
        env.update(
            LLM_PROVIDER="ollama",
            LLM_MODEL=args.model,
            OLLAMA_BASE_URL="http://127.0.0.1:11434",
        )
        if args.neural:
            env.update(EMBEDDING_PROVIDER="ollama", EMBEDDING_MODEL="nomic-embed-text:v1.5")
        if not open_port(11434):
            raise SystemExit("Start Ollama and pull the documented local models first.")
    env["DATABASE_URL"] = "postgresql+psycopg://workflow:workflow@127.0.0.1:55432/workflow"
    env["UV_CACHE_DIR"] = str(ROOT / ".tmp/uv-cache")
    env["UV_PYTHON_INSTALL_DIR"] = str(ROOT / ".local/python")
    env["npm_config_cache"] = str(ROOT / ".tmp/npm-cache")
    if not (ROOT / ".env").exists():
        shutil.copyfile(ROOT / ".env.example", ROOT / ".env")
    if args.setup:
        uv = shutil.which("uv")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not uv or not npm:
            raise SystemExit("Setup requires uv and npm; see README prerequisites.")
        commands = [
            [uv, "sync", "--locked", "--directory", "backend", "--group", "mcp"],
            [npm, "ci", "--prefix", "frontend"],
            [npm, "ci", "--prefix", "tools/local-db"],
        ]
        for command in commands:
            subprocess.run(command, cwd=ROOT, env=env, check=True)
    python = ROOT / "backend/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    vite = ROOT / "frontend/node_modules/vite/bin/vite.js"
    if (
        not python.exists()
        or not vite.exists()
        or not (ROOT / "tools/local-db/node_modules").exists()
    ):
        raise SystemExit("Dependencies missing. Run: python tools/start_demo.py --setup")
    if any(open_port(port) for port in (55432, 8000, 5173)):
        raise SystemExit("A demo port is in use. Stop its owner first; no process was killed.")

    directory = ROOT / ".local/demo-logs"
    directory.mkdir(parents=True, exist_ok=True)
    children, handles = [], []

    def start(label, command, cwd):
        handle = (directory / (label + ".log")).open("w", encoding="utf-8")
        handles.append(handle)
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT)
        children.append(child)
        return child

    try:
        db = start("database", [node, str(ROOT / "tools/local-db/server.mjs")], ROOT)
        wait_for_port(55432, db)
        subprocess.run(
            [str(python), "-m", "scripts.bootstrap"], cwd=ROOT / "backend", env=env, check=True
        )
        backend = start(
            "backend",
            [
                str(python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            ROOT / "backend",
        )
        wait_for_api(backend)
        frontend = start("frontend", [node, str(vite), "--host", "127.0.0.1"], ROOT / "frontend")
        wait_for_port(5173, frontend)
        print(f"{args.provider} demo ready: http://127.0.0.1:5173/", flush=True)
        print("No paid/cloud provider calls. Keep this terminal open.", flush=True)
        print("Ctrl+C stops only processes started by this launcher.", flush=True)
        while True:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A service stopped; inspect .local/demo-logs.")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping owned demo processes.", flush=True)
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in reversed(children):
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
