"""Repo discipline guards: stdlib-only, no network, SKILL.md contract, no stray docs."""

import ast
import re

from tests.conftest import HAR_SKILL_DIR as SKILL_DIR

ALLOWED_STDLIB = {
    "argparse", "ast", "csv", "dataclasses", "datetime", "fnmatch", "html", "json",
    "os", "pathlib", "re", "sys", "typing", "unicodedata", "urllib",
}
INTRA_SKILL = {"audit", "checkers", "eval_rules", "report", "skparse"}
FORBIDDEN = {
    "socket", "subprocess", "ftplib", "smtplib", "telnetlib", "http.client",
    "urllib.request", "urllib.error", "requests",
}


def _script_files():
    return sorted((SKILL_DIR / "scripts").glob("*.py"))


def _imports_of(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
    return names


def test_scripts_import_stdlib_and_intra_skill_only():
    for path in _script_files():
        for name in _imports_of(path):
            root = name.split(".")[0]
            assert name not in FORBIDDEN, "%s imports forbidden module %s" % (path.name, name)
            assert (
                root in ALLOWED_STDLIB or name in INTRA_SKILL
            ), "%s imports non-stdlib module %s" % (path.name, name)


def test_scripts_have_no_network_or_spawn_calls():
    # Anchored to import-statement / call syntax: the harness legitimately
    # *mentions* banned module names inside docstrings, comments, and the
    # eval_rules.py data lists (its whole job is checking against those lists).
    banned = re.compile(
        r"^\s*(?:import|from)\s+(socket|subprocess|ftplib|smtplib|telnetlib|http\.client|urllib\.request|requests)\b"
        r"|\bos\.system\s*\(|\bos\.popen\s*\(",
        re.MULTILINE,
    )
    for path in _script_files():
        source = path.read_text(encoding="utf-8")
        assert not banned.search(source), "%s references banned call patterns" % path.name


def test_skill_md_under_500_lines():
    lines = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) < 500, "SKILL.md has %d lines (limit 500)" % len(lines)


def test_skill_md_frontmatter_has_only_name_and_description():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md must start with a YAML frontmatter block"
    top_keys = set()
    for line in m.group(1).splitlines():
        if line and not line.startswith((" ", "\t")) and ":" in line:
            top_keys.add(line.split(":", 1)[0].strip())
    assert top_keys == {"name", "description"}, top_keys


def test_skill_md_declares_static_evaluation_red_lines():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "不执行" in text, "red line (no executing evaluated scripts) missing"
    assert "不判定恶意" in text, "red line (no malice verdicts) missing"
    assert "无评分" in text or "不做主观评分" in text, "red line (no scoring) missing"


def test_skill_dir_has_no_readme_or_changelog():
    for path in SKILL_DIR.rglob("*"):
        # fixtures/ holds mini skill packages used as evaluation material;
        # their contents (e.g. readme-in-skill/README.md) never count as
        # stray docs of the host skill -- same exemption the E12 check uses.
        if "fixtures" in path.relative_to(SKILL_DIR).parts:
            continue
        name = path.name.upper()
        assert not name.startswith("README"), "stray doc inside skill dir: %s" % path
        assert not name.startswith("CHANGELOG"), "stray doc inside skill dir: %s" % path
        assert not name.startswith("INSTALL"), "stray doc inside skill dir: %s" % path


def test_no_platform_branding_in_skill_dir():
    banned = re.compile(r"WorkBuddy|CodeBuddy", re.IGNORECASE)
    for path in SKILL_DIR.rglob("*"):
        if path.is_file():
            assert not banned.search(
                path.read_text(encoding="utf-8", errors="replace")
            ), "platform branding leaked into %s" % path


def test_openai_yaml_declares_name_and_exit_codes():
    text = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert "name: skill-eval-harness" in text
    assert "0:" in text and "1:" in text and "2:" in text


def test_manifest_covers_all_fixture_dirs():
    manifest = SKILL_DIR / "fixtures" / "MANIFEST.tsv"
    assert manifest.exists(), "fixtures/MANIFEST.tsv required by E9 contract"
    declared = set()
    for line in manifest.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        assert len(parts) == 2, "MANIFEST rows must be relpath<TAB>exit: %r" % line
        assert parts[1] in {"0", "1", "2"}
        # entries point at fixtures/<name>/SKILL.md (or fixtures/<name>):
        # the fixture package directory is the second path segment.
        segments = parts[0].replace("\\", "/").split("/")
        declared.add(segments[1] if segments[0] == "fixtures" and len(segments) > 1
                     else segments[-1])
    actual = {p.name for p in SKILL_DIR.glob("fixtures/*") if p.is_dir()}
    assert declared == actual, "MANIFEST vs fixture dirs mismatch: %s" % (
        declared ^ actual,
    )


def test_data_provenance_records_standard_source():
    text = (SKILL_DIR / "references" / "data-provenance.md").read_text(
        encoding="utf-8"
    )
    assert "agentskills" in text.lower() or "agent skills" in text.lower()
    assert "2026-" in text, "retrieval date required"
