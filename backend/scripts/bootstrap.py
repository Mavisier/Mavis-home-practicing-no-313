import subprocess
import sys
from pathlib import Path

from scripts.seed import seed

if __name__ == "__main__":
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )
    seed()
