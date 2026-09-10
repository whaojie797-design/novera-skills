"""Fixture-level exit-code contract (design doc section 7 baseline)."""

import pytest

from tests.conftest import PUB_FIXTURES as FIXTURES, pub_run as run_cli

VALIDATE_CASES = [
    ("valid-listing.json", 0),
    ("valid-listing.yaml", 0),
    ("missing-tagline.json", 1),
    ("tagline-too-long.json", 1),
    ("bad-pricing.json", 1),
    ("bad-url.json", 1),
    ("screenshot-spec.md", 1),
    ("no-listing-structure.md", 2),
    ("empty.txt", 0),
]

DIFF_CASES = [
    ("valid-pack", 0),
    ("pricing-drift-pack", 1),
    ("version-drift-pack", 1),
    ("case-diff-pack", 0),
]

STATUS_CASES = [
    ("status-valid.csv", 0),
    ("status-bad.csv", 1),
    ("rejected-resubmitted.csv", 0),
    ("status-empty.csv", 2),
]


def _pack_files(name):
    return sorted(p for p in (FIXTURES / name).iterdir() if p.is_file())


@pytest.mark.parametrize(
    "name,expected", VALIDATE_CASES, ids=[c[0] for c in VALIDATE_CASES]
)
def test_validate_fixture_exit_code(name, expected):
    code, out, err = run_cli(["validate", str(FIXTURES / name)])
    assert code == expected, (
        "%s: want exit %d, got %d\nstdout:\n%s\nstderr:\n%s"
        % (name, expected, code, out, err)
    )


@pytest.mark.parametrize(
    "name,expected", DIFF_CASES, ids=[c[0] for c in DIFF_CASES]
)
def test_diff_pack_exit_code(name, expected):
    code, out, err = run_cli(["diff"] + [str(p) for p in _pack_files(name)])
    assert code == expected, (
        "%s: want exit %d, got %d\nstdout:\n%s\nstderr:\n%s"
        % (name, expected, code, out, err)
    )


@pytest.mark.parametrize(
    "name,expected", STATUS_CASES, ids=[c[0] for c in STATUS_CASES]
)
def test_status_fixture_exit_code(name, expected):
    code, out, err = run_cli(["status", str(FIXTURES / name)])
    assert code == expected, (
        "%s: want exit %d, got %d\nstdout:\n%s\nstderr:\n%s"
        % (name, expected, code, out, err)
    )


def test_e2e_mixed_dir_validate():
    code, out, err = run_cli(["validate", str(FIXTURES / "e2e-mixed-dir")])
    assert code == 1, "e2e-mixed-dir: want exit 1 (V1 + V3), got %d\n%s%s" % (code, out, err)
    rules = {ln.split("rule=")[1].split()[0] for ln in out.splitlines() if "rule=" in ln}
    assert rules == {"V1", "V3"}, rules
