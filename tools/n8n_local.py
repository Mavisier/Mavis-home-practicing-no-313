"""Optional local n8n launcher; no globally installed binary or printed tokens."""

import subprocess
import sys

from integration_env import environment, n8n_command

if __name__ == "__main__":
    result = subprocess.run(n8n_command(*sys.argv[1:]), env=environment())
    raise SystemExit(result.returncode)
