import subprocess
import sys
from pathlib import Path


def test_smoke_runtime_fast():
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "smoke_runtime.py"

    proc = subprocess.run(
        [sys.executable, str(script), "--iterations", "40", "--seed", "20260213"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=15,
    )

    if proc.returncode != 0:
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        raise AssertionError(
            "smoke_runtime.py failed with non-zero exit code.\n"
            f"stdout:\n{out}\n"
            f"stderr:\n{err}\n"
        )

    out = proc.stdout.strip()
    assert "smoke_runtime summary:" in out
    assert "3BET=" in out
