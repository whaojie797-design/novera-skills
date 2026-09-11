"""Shared helpers for ALL skill test suites in the mono-repo.

A single top-level conftest avoids pytest prepend-mode name clashes between
per-skill conftest modules. Test files import their constants via aliases:

    from conftest import GEO_FIXTURES as FIXTURES, geo_run as run_cli
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = REPO_ROOT / "skills"


def _make_runner(audit):
    def run(args, cwd=None):
        proc = subprocess.run(
            [sys.executable, str(audit)] + [str(a) for a in args],
            capture_output=True,
            text=True,
            cwd=str(cwd or REPO_ROOT),
        )
        return proc.returncode, proc.stdout, proc.stderr

    return run


# --- geo-evidence-audit -------------------------------------------------
GEO_SKILL_DIR = SKILLS / "geo-evidence-audit"
GEO_FIXTURES = GEO_SKILL_DIR / "fixtures"
GEO_E2E_DIR = GEO_FIXTURES / "e2e-mixed-dir"
geo_run = _make_runner(GEO_SKILL_DIR / "scripts" / "audit.py")

# --- ai-tool-directory-publisher ---------------------------------------
PUB_SKILL_DIR = SKILLS / "ai-tool-directory-publisher"
PUB_FIXTURES = PUB_SKILL_DIR / "fixtures"
PUB_E2E_DIR = PUB_FIXTURES / "e2e-mixed-dir"
pub_run = _make_runner(PUB_SKILL_DIR / "scripts" / "audit.py")

# --- skill-eval-harness -------------------------------------------------
HAR_SKILL_DIR = SKILLS / "skill-eval-harness"
HAR_FIXTURES = HAR_SKILL_DIR / "fixtures"
HAR_E2E_DIR = HAR_FIXTURES / "e2e-demo"
har_run = _make_runner(HAR_SKILL_DIR / "scripts" / "audit.py")

# --- skill-supply-chain-audit -------------------------------------------
SCA_SKILL_DIR = SKILLS / "skill-supply-chain-audit"
SCA_FIXTURES = SCA_SKILL_DIR / "fixtures"
SCA_E2E_DIR = SCA_FIXTURES / "e2e-pack"
sca_run = _make_runner(SCA_SKILL_DIR / "scripts" / "audit.py")

# --- commerce-visual-brief ----------------------------------------------
CVB_SKILL_DIR = SKILLS / "commerce-visual-brief"
CVB_FIXTURES = CVB_SKILL_DIR / "fixtures"
CVB_E2E_DIR = CVB_FIXTURES / "e2e-mixed-dir"
cvb_run = _make_runner(CVB_SKILL_DIR / "scripts" / "audit.py")


def mini_dir(name):
    """Deterministic overwrite-only mini directory (deletion-free by
    design: local safe-delete hooks fail closed on bulk cleanups; CI is
    unaffected). Lives under the gitignored .pytest_cache."""
    d = REPO_ROOT / ".pytest_cache" / "mini" / name
    d.mkdir(parents=True, exist_ok=True)
    return d
