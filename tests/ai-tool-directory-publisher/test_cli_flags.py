"""CLI flag behavior: --directory, --include-unverified, --format/--output/--quiet, exit code 2."""

import json

from conftest import FIXTURES, run_cli


def test_directory_filter_runs_only_selected_spec():
    code, out, err = run_cli(
        ["validate", str(FIXTURES / "missing-tagline.json"), "--directory", "toolify"]
    )
    assert code == 1
    findings = [ln for ln in out.splitlines() if "rule=" in ln]
    assert len(findings) == 1, out


def test_directory_filter_unknown_slug_is_usage_error():
    code, _, _ = run_cli(
        ["validate", str(FIXTURES / "missing-tagline.json"), "--directory", "bogus"]
    )
    assert code == 2


def test_include_unverified_off_by_default():
    code, out, err = run_cli(
        ["validate", str(FIXTURES / "aitools-fyi-missing-tagline.json")]
    )
    assert code == 0, "unverified-only spec must be skipped by default\n%s%s" % (out, err)
    assert "unverified" not in out.lower() or "0 findings" in out


def test_include_unverified_reports_labeled_findings():
    code, out, err = run_cli(
        [
            "validate",
            str(FIXTURES / "aitools-fyi-missing-tagline.json"),
            "--include-unverified",
        ]
    )
    assert code == 1
    assert "unverified" in out, "finding must be labeled unverified\n%s" % out


def test_diff_needs_two_files():
    code, _, _ = run_cli(["diff", str(FIXTURES / "missing-tagline.json")])
    assert code == 2


def test_diff_needs_subcommand_args():
    code, _, _ = run_cli(["diff"])
    assert code == 2


def test_missing_subcommand_is_usage_error():
    code, _, _ = run_cli([])
    assert code == 2


def test_missing_path_is_usage_error():
    code, _, _ = run_cli(["validate", str(FIXTURES / "does-not-exist.json")])
    assert code == 2


def test_quiet_prints_finding_lines_and_count_only():
    code, out, err = run_cli(["validate", str(FIXTURES / "bad-pricing.json"), "--quiet"])
    assert code == 1
    assert "expected:" not in out, "--quiet must not print finding details"
    assert "1 findings." in out


def test_output_writes_file_and_keeps_stdout_empty(tmp_path):
    target = tmp_path / "report.txt"
    code, out, err = run_cli(
        ["validate", str(FIXTURES / "bad-pricing.json"), "--output", str(target)]
    )
    assert code == 1
    assert out == "", "--output must not duplicate report on stdout"
    content = target.read_text(encoding="utf-8")
    assert "[finding]" in content


def test_json_report_is_parseable_with_expected_fields(tmp_path):
    target = tmp_path / "report.json"
    code, _, _ = run_cli(
        ["validate", str(FIXTURES / "bad-pricing.json"), "--format", "json",
         "--output", str(target)]
    )
    assert code == 1
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["summary"]["findings"] >= 1
    for f in data["findings"]:
        for key in ("file", "line", "rule", "strength", "field", "value", "expected"):
            assert key in f, "finding missing key %s" % key
