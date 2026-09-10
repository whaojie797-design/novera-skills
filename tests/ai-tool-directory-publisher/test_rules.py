"""Rule-level guarantees: finding fields, drift contrast, status integrity, determinism."""

import json
import re

from conftest import FIXTURES, run_cli

FINDING_KEYS = {"file", "line", "rule", "strength", "field", "value", "expected"}


def _json_out(subcommand, *paths):
    code, out, err = run_cli([subcommand] + [str(p) for p in paths] + ["--format", "json"])
    assert code in (0, 1), "want 0/1, got %d\n%s%s" % (code, out, err)
    return json.loads(out), code


def test_pricing_drift_reports_both_sides():
    pack = FIXTURES / "pricing-drift-pack"
    files = sorted(p for p in pack.iterdir() if p.is_file())
    data, code = _json_out("diff", *files)
    assert code == 1
    drift = [f for f in data["findings"] if f["rule"] == "C1"]
    assert drift, "expected C1 drift finding"
    d = drift[0]
    assert d["strength"] == "inferred"
    # the finding must reference both sides' values
    assert "free" in str(d["value"]).lower() or "paid" in str(d["value"]).lower()


def test_case_normalized_pricing_is_not_drift():
    pack = FIXTURES / "case-diff-pack"
    files = sorted(p for p in pack.iterdir() if p.is_file())
    data, code = _json_out("diff", *files)
    assert code == 0 and data["summary"]["findings"] == 0


def test_status_bad_reports_two_problems():
    data, code = _json_out("status", FIXTURES / "status-bad.csv")
    assert code == 1
    s1 = [f for f in data["findings"] if f["rule"] == "S1"]
    assert len(s1) == 2, s1
    for f in s1:
        assert f["file"] and isinstance(f["line"], int) and f["line"] >= 1


def test_snapshot_findings_carry_provenance_hint():
    _, out, _ = run_cli(["validate", str(FIXTURES / "bad-pricing.json")])
    assert "data-provenance" in out or "official site is authoritative" in out, (
        "snapshot-based findings must carry the 'official site is authoritative' hint"
    )


def test_findings_have_file_line_in_text_mode():
    _, out, _ = run_cli(["validate", str(FIXTURES / "e2e-mixed-dir")])
    finding_lines = [ln for ln in out.splitlines() if ln.startswith("[finding]")]
    assert len(finding_lines) == 2
    for ln in finding_lines:
        assert re.search(r"\[finding\] \S+:\d+", ln), "missing file:line in %r" % ln


def test_deterministic_output():
    args = ["validate", str(FIXTURES / "bad-pricing.json"), "--format", "json"]
    _, out1, _ = run_cli(args)
    _, out2, _ = run_cli(args)
    assert out1 == out2, "same input must produce byte-identical output"
