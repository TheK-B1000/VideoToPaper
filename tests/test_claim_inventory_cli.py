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


def test_speaker_perspective_module_runs_help():
    result = subprocess.run(
        [sys.executable, "-m", "src.pipelines.run_steelman_pipeline", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--claim-inventory-path" in result.stdout


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


def test_main_py_steelman_stage_forwards_argv_to_run_steelman_parser():
    """Unknown flags after --stage steelman are parsed by run_steelman_pipeline (not main)."""
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--stage",
            "steelman",
            "--not-a-real-arg",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    combined = result.stderr + result.stdout
    assert "--config-path" in combined
    assert "unrecognized arguments" in combined.lower()
