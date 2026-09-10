"""CLI flag behavior: --profile, --only, --format/--output/--quiet, exit code 2."""

import json

from tests.conftest import HAR_FIXTURES as FIXTURES, REPO_ROOT, HAR_SKILL_DIR as SKILL_DIR, har_run as run_cli


def test_exit_2_missing_directory():
    code, _, _ = run_cli([str(FIXTURES / "no-such-dir")])
    assert code == 2


def test_exit_2_bad_only_id():
    code, _, _ = run_cli([str(FIXTURES / "network-call"), "--only", "E99"])
    assert code == 2


def test_exit_2_no_arguments():
    code, _, _ = run_cli([])
    assert code == 2


def test_only_accepts_comma_list():
    code, out, err = run_cli([str(FIXTURES / "bad-frontmatter"), "--only", "E1,E2"])
    assert code == 1
    rules = {ln.split("rule=")[1].split()[0] for ln in out.splitlines() if "rule=" in ln}
    assert rules == {"E1"}, rules


def test_quiet_prints_finding_lines_and_count_only():
    code, out, err = run_cli([str(FIXTURES / "bad-frontmatter"), "--quiet"])
    assert code == 1
    assert "issue:" not in out, "--quiet must not print finding details"
    assert "1 finding" in out


def test_output_writes_file_and_keeps_stdout_empty(tmp_path):
    target = tmp_path / "report.txt"
    code, out, err = run_cli(
        [str(FIXTURES / "bad-frontmatter"), "--output", str(target)]
    )
    assert code == 1
    assert out == "", "--output must not duplicate report on stdout"
    content = target.read_text(encoding="utf-8")
    assert "[finding]" in content


def test_json_report_schema(tmp_path):
    target = tmp_path / "report.json"
    code, _, _ = run_cli(
        [str(FIXTURES / "bad-frontmatter"), "--format", "json", "--output", str(target)]
    )
    assert code == 1
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["summary"]["findings"] >= 1
    assert data["checks_run"] >= 1
    for f in data["findings"]:
        for key in ("file", "line", "rule", "strength", "issue", "basis"):
            assert key in f, "finding missing key %s" % key


def test_bootstrap_three_own_skills_clean():
    for slug in (
        "geo-evidence-audit",
        "ai-tool-directory-publisher",
        "skill-eval-harness",
    ):
        code, out, err = run_cli([str(REPO_ROOT / "skills" / slug)])
        assert code == 0, (
            "bootstrap: own skill %s must pass novera profile\n%s%s" % (slug, out, err)
        )


def test_report_header_carries_profile_and_counts():
    code, out, err = run_cli([str(FIXTURES / "e2e-demo")])
    assert code == 1
    assert "profile: novera" in out
    assert "checks: 12 run / 0 skipped" in out
    assert "summary: 1 finding across 12 checks. exit code: 1" in out
