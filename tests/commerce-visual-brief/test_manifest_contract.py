"""Fixture-level exit-code contract for commerce-visual-brief.

Every data row mirrors fixtures/MANIFEST.tsv, the single source of truth.
Rows exercising V6-V9 need --platform and therefore exit 0 under the bare
manifest semantics (validate, no extra flags); their flag-on behavior is
covered in test_rules.py.
"""

import pytest

from tests.conftest import (
    CVB_E2E_DIR as E2E_DIR,
    CVB_FIXTURES as FIXTURES,
    cvb_run as run_cli,
)

# (relpath, expected exit) -- mirrors MANIFEST.tsv data rows in order
CASES = [
    ("valid-brief.md", 0),
    ("valid-brief.json", 0),
    ("missing-pricing.md", 1),
    ("missing-color-card.md", 1),
    ("currency-mismatch.md", 1),
    ("extreme-words.md", 1),
    ("claim-no-evidence.md", 1),
    ("category-scene-mismatch.md", 1),
    ("image-spec-mismatch.md", 0),
    ("main-image-count.md", 0),
    ("missing-compliance-decl.md", 1),
    ("no-brief-structure.md", 2),
    ("empty.txt", 2),
    ("comparative-words.md", 0),
    ("e2e-mixed-dir", 1),
    ("category-scene-unknown.md", 0),
    ("unverified-platform.md", 0),
]


@pytest.mark.parametrize("rel,expected", CASES, ids=[c[0] for c in CASES])
def test_manifest_exit_codes(rel, expected):
    code, out, err = run_cli(["validate", str(FIXTURES / rel)])
    assert code == expected, (
        "fixtures/%s: want exit %d, got %d\nstdout:\n%s\nstderr:\n%s"
        % (rel, expected, code, out, err)
    )


RULE_IDS = {"V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10"}


def _rules(out):
    rules = set()
    for ln in out.splitlines():
        head = ln.split()
        if head and head[0] in RULE_IDS:
            rules.add(head[0])
    return rules


def test_e2e_dir_validate_yields_v1_and_v10():
    # trailing slash keeps reported paths relative to the scanned dir,
    # mirroring the SKILL.md end-to-end example
    code, out, err = run_cli(["validate", str(E2E_DIR) + "/",
                              "--platform", "taobao"])
    assert code == 1, out + err
    assert _rules(out) == {"V1", "V10"}, out
    assert "findings: 2" in out


def test_e2e_dir_inventory_lists_three_placements():
    code, out, err = run_cli(["inventory", str(E2E_DIR) + "/"])
    assert code == 0, out + err
    assert "inventory: 3 item(s)" in out
    assert "placement brief-a.md:8" in out
    assert "placement brief-b.md:9" in out
    assert "placement brief-clean.md:11" in out


def test_manifest_tsv_wellformed():
    path = FIXTURES / "MANIFEST.tsv"
    rows = [ln for ln in path.read_text(encoding="utf-8-sig").splitlines()
            if ln and not ln.startswith("#")]
    assert len(rows) == 17, "expect exactly 17 contract rows, got %d" % len(rows)
    for row in rows:
        relpath, expected = row.split("\t")
        assert expected in ("0", "1", "2"), row
        assert (FIXTURES / relpath).exists(), "missing fixture: " + relpath
    # manifest order must mirror CASES order (single source of truth)
    assert [r.split("\t")[0] for r in rows] == [c[0] for c in CASES]


def test_manifest_flags_unverified_row_semantics():
    # the manifest header must document the flag-on behaviors that the
    # bare exit codes cannot express (V6-V9 need --platform; #17 switches)
    text = (FIXTURES / "MANIFEST.tsv").read_text(encoding="utf-8-sig")
    assert "--platform amazon" in text
    assert "--include-unverified" in text
