import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_claim_inventory_module_runs_help():
    result = subprocess.run(
        [sys.executable, "-m", "src.pipelines.claim_inventory_pipeline", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--chunks-path" in result.stdout


def test_main_py_claim_inventory_stage_runs_help_via_known_args():
    result = subprocess.run(
        [sys.executable, "main.py", "--stage", "claim_inventory", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--stage" in result.stdout
