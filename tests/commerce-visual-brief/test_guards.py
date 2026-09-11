"""Honesty, robustness and structural guards for commerce-visual-brief."""

import ast
import json
import subprocess
import sys

import pytest

from tests.conftest import (
    REPO_ROOT,
    CVB_FIXTURES as FIXTURES,
    CVB_SKILL_DIR as SKILL_DIR,
    cvb_run as run_cli,
)


# --- exit code 2 (usage / input errors) ------------------------------------

def test_no_subcommand_exits_two():
    code, out, err = run_cli([])
    assert code == 2
    assert "subcommand" in err


def test_unknown_platform_exits_two():
    code, out, err = run_cli(["validate", str(FIXTURES / "valid-brief.md"),
                              "--platform", "bogus"])
    assert code == 2
    assert "unknown platform slug" in err
    assert "amazon" in err          # valid slugs are listed


def test_missing_path_exits_two():
    code, out, err = run_cli(["validate",
                              str(FIXTURES / "no-such-file.md")])
    assert code == 2
    assert "path not found" in err


def test_no_brief_structure_exits_two():
    code, out, err = run_cli(["validate",
                              str(FIXTURES / "no-brief-structure.md")])
    assert code == 2
    assert "no brief structure" in err
    assert "1 file(s) scanned" in err


def test_empty_file_exits_two():
    code, out, err = run_cli(["validate", str(FIXTURES / "empty.txt")])
    assert code == 2
    assert "no brief structure" in err


# --- determinism -------------------------------------------------------------

@pytest.mark.parametrize("fmt", ["text", "json"])
def test_output_is_byte_deterministic(fmt):
    a = run_cli(["validate", str(FIXTURES / "extreme-words.md"),
                 "--format", fmt])
    b = run_cli(["validate", str(FIXTURES / "extreme-words.md"),
                 "--format", fmt])
    assert a == b


def test_format_does_not_change_exit_code():
    base = ["validate", str(FIXTURES / "extreme-words.md")]
    results = [run_cli(base + ["--format", fmt])[0]
               for fmt in ("text", "json")]
    assert results == [1, 1]


def test_json_output_sorted_and_stable():
    _, out, _ = run_cli(["validate", str(FIXTURES / "valid-brief.md"),
                         "--format", "json"])
    doc = json.loads(out)
    assert doc["findings"] == []
    assert doc["exit_code"] == 0
    assert set(doc) >= {"version", "command", "findings", "inventory",
                        "exit_code", "summary"}


# --- package structure & stdlib guard ----------------------------------------

def test_skillmd_frontmatter_and_length():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) < 500
    assert lines[0] == "---"
    end = lines.index("---", 1)
    fm = "\n".join(lines[1:end])
    # only top-level (non-indented) lines are keys; the multi-line folded
    # description continuation lines must not be mistaken for keys
    keys = [ln.split(":", 1)[0] for ln in fm.splitlines()
            if ln.strip() and not ln[:1].isspace()]
    assert keys == ["name", "description"], keys


def test_skillmd_honesty_strings_present():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "not a legal determination" in text
    assert "以平台规范为准，快照会过期" in text
    assert "inventory != risk" in text or "≠ 风险" in text
    assert "--include-unverified" in text


def test_openai_yaml_present_no_readme_changelog():
    assert (SKILL_DIR / "agents" / "openai.yaml").is_file()
    names = {p.name.lower() for p in SKILL_DIR.rglob("*") if p.is_file()}
    assert not any(n.startswith("readme") for n in names)
    assert not any(n.startswith("changelog") for n in names)


def test_references_complete():
    refs = {p.name for p in (SKILL_DIR / "references").glob("*.md")}
    assert refs == {"rules.md", "data-provenance.md", "evidence-model.md",
                    "scope.md", "brief-template.md"}, refs


def test_scripts_are_stdlib_only():
    allowed = {"argparse", "dataclasses", "fnmatch", "json", "os", "re",
               "sys", "typing"}
    intra = {"audit", "brief_data", "briefparse", "checkers",
             "platform_specs", "report"}
    scripts = sorted((SKILL_DIR / "scripts").glob("*.py"))
    assert len(scripts) == 6
    for path in scripts:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 \
                    and node.module:
                mods = [node.module.split(".")[0]]
            for m in mods:
                assert m in allowed or m in intra, \
                    "%s imports %s" % (path.name, m)


def test_platform_specs_unverified_entries_carry_no_numbers():
    # honesty red line: unverified platform entries must have empty numeric
    # fields -- read as data, not as source text
    sys.path.insert(0, str(SKILL_DIR / "scripts"))
    try:
        import platform_specs
        for slug in ("taobao", "tmall", "jd", "pdd"):
            spec = platform_specs.PLATFORMS[slug]
            assert spec.verified is False, slug
            assert spec.formats == (), slug
            assert spec.min_long_side is None, slug
            assert spec.max_long_side is None, slug
            assert spec.main_image_count is None, slug
            assert spec.product_fills_percent is None, slug
            assert spec.whitespace_required is None, slug
        amazon = platform_specs.PLATFORMS["amazon"]
        assert amazon.verified is True
        assert amazon.source_url.startswith("https://")
        assert amazon.snapshot_date == "2026-09-11"
        assert amazon.min_long_side == 500
        assert amazon.max_long_side == 10000
    finally:
        sys.path.pop(0)
        sys.modules.pop("platform_specs", None)


def test_py39_gate_passes_on_all_modules():
    gate = REPO_ROOT / "tools" / "py39_gate.py"
    mods = sorted((SKILL_DIR / "scripts").glob("*.py"))
    proc = subprocess.run(
        [sys.executable, str(gate)] + [str(m) for m in mods],
        capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "0 incompatible" in proc.stdout
