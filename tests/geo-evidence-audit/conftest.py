"""Shared helpers for geo-evidence-audit tests.

Tests run the real CLI via subprocess (no in-process import), mirroring how
the skill is actually invoked.
"""

import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent          # .../tests/geo-evidence-audit
REPO_ROOT = TESTS_DIR.parents[1]                     # novera-skills repo root
SKILL_DIR = REPO_ROOT / "skills" / "geo-evidence-audit"
AUDIT = SKILL_DIR / "scripts" / "audit.py"
FIXTURES = SKILL_DIR / "fixtures"
E2E_DIR = FIXTURES / "e2e-mixed-dir"


def run_cli(args, cwd=None):
    """Run scripts/audit.py with the current interpreter. Returns (code, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(AUDIT)] + [str(a) for a in args],
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
    )
    return proc.returncode, proc.stdout, proc.stderr
