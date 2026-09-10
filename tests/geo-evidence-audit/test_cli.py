"""CLI flag behavior: --min-strength, --rules, --exclude, --quiet, --output, exit code 2."""

import json

from tests.conftest import GEO_E2E_DIR as E2E_DIR, GEO_FIXTURES as FIXTURES, geo_run as run_cli


def test_min_strength_explicit_filters_inferred_and_unverified():
    # R1-R4 are inferred, so lowering the floor to explicit silences everything
    code, out, err = run_cli([FIXTURES / "multi-contradictions.md", "--min-strength", "explicit"])
    assert code == 0, out + err
    code, out, err = run_cli([FIXTURES / "unverified-city.md", "--min-strength", "explicit"])
    assert code == 0, out + err


def test_rules_filter_runs_only_selected_rule():
    code, out, err = run_cli([FIXTURES / "multi-contradictions.md", "--rules", "R1"])
    assert code == 1
    rules = [ln.split("rule=")[1].split()[0] for ln in out.splitlines() if "rule=" in ln]
    assert rules == ["R1"], rules


def test_exclude_removes_matching_files_in_dir_mode():
    code, out, err = run_cli([E2E_DIR, "--exclude", "unverified*"])
    assert code == 1
    assert "rule=R7" not in out, "excluded file still audited"
    assert "rule=R1" in out


def test_quiet_prints_finding_lines_and_count_only():
    code, out, err = run_cli([FIXTURES / "phone-mismatch.md", "--quiet"])
    assert code == 1
    assert "conflict:" not in out, "--quiet must not print finding details"
    assert "1 findings." in out


def test_output_writes_file_and_keeps_stdout_empty(tmp_path):
    target = tmp_path / "report.txt"
    code, out, err = run_cli(
        [FIXTURES / "phone-mismatch.md", "--output", str(target)]
    )
    assert code == 1
    assert out == "", "--output must not duplicate report on stdout"
    content = target.read_text(encoding="utf-8")
    assert "[finding]" in content


def test_output_json_report_is_parseable(tmp_path):
    target = tmp_path / "report.json"
    code, _, _ = run_cli(
        [FIXTURES / "phone-mismatch.md", "--format", "json", "--output", str(target)]
    )
    assert code == 1
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["summary"]["findings"] == 1


def test_exit_2_missing_path():
    code, _, _ = run_cli([FIXTURES / "does-not-exist.md"])
    assert code == 2


def test_exit_2_bad_format():
    code, _, _ = run_cli([FIXTURES / "phone-mismatch.md", "--format", "bogus"])
    assert code == 2


def test_exit_2_no_auditable_files(tmp_path):
    (tmp_path / "a.xyz").write_text("hello", encoding="utf-8")
    (tmp_path / "b.bin").write_bytes(b"\x00\x01")
    code, out, err = run_cli([tmp_path])
    assert code == 2, "directory with zero auditable files must exit 2\n%s%s" % (out, err)
