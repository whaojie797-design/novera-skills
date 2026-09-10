"""Fixture-level exit-code contract (design doc section 7 baseline)."""

import pytest

from tests.conftest import GEO_E2E_DIR as E2E_DIR, GEO_FIXTURES as FIXTURES, geo_run as run_cli

# (fixture name, expected exit code) -- from DESIGN-geo-evidence-audit-v0.1.md section 7
CASES = [
    ("consistent-office-cn.md", 0),
    ("consistent-office-de.html", 0),
    ("phone-mismatch.md", 1),
    ("timezone-mismatch.md", 1),
    ("currency-mismatch.md", 1),
    ("coord-outside-bbox.md", 1),
    ("hreflang-mismatch.html", 1),
    ("map-embed-mismatch.html", 1),
    ("unverified-city.md", 1),
    ("multi-contradictions.md", 1),
    ("stores.json", 1),
    ("offices.csv", 1),
    ("no-geo-claims.md", 0),
    ("empty.txt", 0),
]


@pytest.mark.parametrize(
    "name,expected", CASES, ids=[c[0] for c in CASES]
)
def test_fixture_exit_code(name, expected):
    code, out, err = run_cli([FIXTURES / name])
    assert code == expected, (
        "fixture %s: want exit %d, got %d\nstdout:\n%s\nstderr:\n%s"
        % (name, expected, code, out, err)
    )


def test_e2e_dir_exit_code():
    code, out, err = run_cli([E2E_DIR])
    assert code == 1, "e2e-mixed-dir: want exit 1 (R1 + R7), got %d\n%s%s" % (code, out, err)
