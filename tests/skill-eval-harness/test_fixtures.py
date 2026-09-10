"""Fixture-level exit-code contract (design doc section 7 baseline)."""

import pytest

from tests.conftest import HAR_FIXTURES as FIXTURES, har_run as run_cli

# (fixture dir, expected exit code under default novera profile)
CASES = [
    ("good-skill", 0),
    ("bad-frontmatter", 1),
    ("too-long-skillmd", 1),
    ("missing-triggers", 1),
    ("third-party-import", 1),
    ("network-call", 1),
    ("no-openai-yaml", 1),
    ("empty-references", 1),
    ("no-exit-code-doc", 1),
    ("broken-syntax", 1),
    ("fixtures-missing", 1),
    ("readme-in-skill", 1),
    ("not-a-skill", 2),
    ("e2e-demo", 1),
]


@pytest.mark.parametrize("name,expected", CASES, ids=[c[0] for c in CASES])
def test_fixture_exit_code(name, expected):
    code, out, err = run_cli([str(FIXTURES / name)])
    assert code == expected, (
        "%s: want exit %d, got %d\nstdout:\n%s\nstderr:\n%s"
        % (name, expected, code, out, err)
    )


def test_minimal_ok_dual_profile():
    code, out, err = run_cli([str(FIXTURES / "minimal-ok"), "--profile", "minimal"])
    assert code == 0, out + err
    code, out, err = run_cli([str(FIXTURES / "minimal-ok")])
    assert code == 1, "novera profile must flag the missing 8+4+1 inventory\n" + out


@pytest.mark.parametrize(
    "name", ["comment-mention", "line-499", "urllib-parse-ok"]
)
def test_counter_examples_stay_clean(name):
    code, out, err = run_cli([str(FIXTURES / name)])
    assert code == 0, "counter-example %s must not trigger findings\n%s%s" % (
        name, out, err,
    )


def test_network_call_reports_e5_and_e6():
    code, out, err = run_cli([str(FIXTURES / "network-call")])
    assert code == 1
    rules = {ln.split("rule=")[1].split()[0] for ln in out.splitlines() if "rule=" in ln}
    assert rules == {"E5", "E6"}, rules


def test_only_e5_narrows_network_call():
    code, out, err = run_cli([str(FIXTURES / "network-call"), "--only", "E5"])
    assert code == 1
    rules = {ln.split("rule=")[1].split()[0] for ln in out.splitlines() if "rule=" in ln}
    assert rules == {"E5"}, rules
