"""Rule composition, JSON report contract, determinism, file:line guarantee."""

import json
import re

from conftest import E2E_DIR, FIXTURES, run_cli

FINDING_KEYS = {"claimed", "conflict", "file", "line", "rule", "severity", "strength"}


def _json_findings(args):
    code, out, err = run_cli(args + ["--format", "json"])
    assert code == 1, "want exit 1, got %d\n%s%s" % (code, out, err)
    data = json.loads(out)
    return data


def test_multi_contradictions_rule_composition():
    data = _json_findings([FIXTURES / "multi-contradictions.md"])
    rules = [f["rule"] for f in data["findings"]]
    assert sorted(rules) == ["R1", "R2", "R3", "R4"], rules


def test_e2e_dir_rule_composition_and_severity():
    data = _json_findings([E2E_DIR])
    by_rule = {f["rule"]: f for f in data["findings"]}
    assert set(by_rule) == {"R1", "R7"}, by_rule
    assert by_rule["R1"]["severity"] == "error"
    assert by_rule["R7"]["severity"] == "info"
    assert by_rule["R1"]["strength"] == "inferred"
    assert by_rule["R7"]["strength"] == "unverified"


def test_json_finding_fields_complete():
    data = _json_findings([E2E_DIR])
    assert data["summary"]["findings"] == len(data["findings"])
    for f in data["findings"]:
        missing = FINDING_KEYS - set(f)
        assert not missing, "finding missing keys: %s" % missing
        assert isinstance(f["line"], int) and f["line"] >= 1
        assert f["file"], "file must be non-empty"


def test_json_notes_carry_disclaimers():
    data = _json_findings([E2E_DIR])
    notes = " ".join(data.get("notes", []))
    assert "NOT precise reverse geocoding" in notes
    assert "unverified does not mean false" in notes


def test_text_findings_have_file_line():
    code, out, err = run_cli([FIXTURES / "multi-contradictions.md"])
    assert code == 1
    finding_lines = [ln for ln in out.splitlines() if ln.startswith("[finding]")]
    assert len(finding_lines) == 4
    for ln in finding_lines:
        assert re.search(r"\[finding\] \S+:\d+", ln), "missing file:line in %r" % ln


def test_deterministic_output():
    args = [FIXTURES / "multi-contradictions.md", "--format", "json"]
    _, out1, _ = run_cli(args)
    _, out2, _ = run_cli(args)
    assert out1 == out2, "same input must produce byte-identical output"


def test_counter_examples_stay_silent():
    # R3 counter-example: eurozone member may use EUR
    code, out, err = run_cli([E2E_DIR / "euro-member.md"])
    assert code == 0, out + err
    # R2 counter-example: multi-timezone country, any tz band matches
    code, out, err = run_cli([E2E_DIR / "usa-multitz.md"])
    assert code == 0, out + err
