"""Fixture-level exit-code contract (MANIFEST.tsv, design section 7 baseline).

Snapshot entries are profile commands over the sibling *.json files of the
same prefix; package entries are refs/chain over mini skill directories.
Every case mirrors MANIFEST.tsv, which is the single source of truth.
"""

import pytest

from tests.conftest import (
    SCA_E2E_DIR as E2E_DIR,
    SCA_FIXTURES as FIXTURES,
    sca_run as run_cli,
)

# (kind, name, companions/extras, expected exit) -- kind: profile|refs|chain
CASES = [
    ("profile", "healthy-repo.json",
     ["healthy-commits.json", "healthy-contributors.json",
      "--releases", "healthy-releases.json"], 0),
    ("profile", "stale-repo.json",
     ["stale-commits.json", "stale-contributors.json"], 1),
    ("profile", "archived-repo.json",
     ["archived-commits.json", "archived-contributors.json"], 1),
    ("profile", "no-release-repo.json",
     ["no-release-commits.json", "no-release-contributors.json",
      "--releases", "no-release-releases.json"], 1),
    ("profile", "malformed-export.json",
     ["healthy-commits.json", "healthy-contributors.json"], 2),
    ("profile", "schema-missing-export.json",
     ["healthy-commits.json", "healthy-contributors.json"], 2),
    ("profile", "no-fetched-at-export.json",
     ["no-fetched-at-commits.json", "no-fetched-at-contributors.json"], 1),
    ("refs", "refs-clean", [], 0),
    ("refs", "refs-external", [], 1),
    ("refs", "endpoints-raw-ip", [], 1),
    ("chain", "chain-curl-sh", [], 1),
    ("chain", "npm-official-prompt", [], 0),
    ("chain", "npm-unofficial-prompt", [], 1),
    ("chain", "same-name-known", [], 0),
]


def _args(kind, name, extras):
    if kind == "profile":
        args = ["profile", str(FIXTURES / name)]
        for item in extras:
            args.append(item if item.startswith("--")
                        else str(FIXTURES / item))
        return args
    return [kind, str(FIXTURES / name)]


@pytest.mark.parametrize(
    "kind,name,extras,expected",
    CASES,
    ids=["%s-%s" % (c[0], c[1]) for c in CASES],
)
def test_manifest_exit_codes(kind, name, extras, expected):
    code, out, err = run_cli(_args(kind, name, extras))
    assert code == expected, (
        "%s/%s: want exit %d, got %d\nstdout:\n%s\nstderr:\n%s"
        % (kind, name, expected, code, out, err)
    )


@pytest.mark.parametrize("sub", ["profile", "refs", "chain"])
def test_e2e_pack_each_subcommand_finds_exactly_one(sub):
    if sub == "profile":
        args = [sub, str(E2E_DIR / "snapshots" / "repo.json"),
                str(E2E_DIR / "snapshots" / "commits.json"),
                str(E2E_DIR / "snapshots" / "contributors.json")]
    else:
        args = [sub, str(E2E_DIR)]
    code, out, err = run_cli(args)
    assert code == 1, "%s on e2e-pack: want 1, got %d\n%s\n%s" % (
        sub, code, out, err)
    n = out.count("[finding]")
    assert n == 1, "%s on e2e-pack: want 1 finding, got %d\n%s" % (
        sub, n, out)


def test_e2e_pack_combined_findings_equal_three():
    total = 0
    for sub in ("profile", "refs", "chain"):
        if sub == "profile":
            args = [sub, str(E2E_DIR / "snapshots" / "repo.json"),
                    str(E2E_DIR / "snapshots" / "commits.json"),
                    str(E2E_DIR / "snapshots" / "contributors.json")]
        else:
            args = [sub, str(E2E_DIR)]
        code, out, err = run_cli(args)
        assert code == 1
        total += out.count("[finding]")
    assert total == 3, "e2e-pack combined findings: want 3, got %d" % total


def test_manifest_tsv_wellformed():
    path = FIXTURES / "MANIFEST.tsv"
    rows = [ln for ln in path.read_text(encoding="utf-8-sig")
            .splitlines() if ln and not ln.startswith("#")]
    assert len(rows) == 15, "expect exactly 15 contract rows, got %d" % len(rows)
    for row in rows:
        relpath, expected = row.split("\t")
        assert expected in ("0", "1", "2"), row
        assert (FIXTURES.parent / relpath).exists() or \
               (FIXTURES / relpath).exists(), "missing fixture: " + relpath
