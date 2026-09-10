"""Repo discipline guards: stdlib-only, no network, SKILL.md contract, no stray docs."""

import ast
import re
from pathlib import Path

from tests.conftest import PUB_SKILL_DIR as SKILL_DIR

# Standard-library modules allowed inside scripts/ (plus intra-skill imports below).
ALLOWED_STDLIB = {
    "argparse", "ast", "csv", "dataclasses", "datetime", "fnmatch", "html", "json",
    "os", "pathlib", "re", "sys", "typing", "unicodedata", "urllib",
}
INTRA_SKILL = {"audit", "listing", "directory_data", "checkers", "report"}
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
    banned = re.compile(
        r"urllib\.request|urlopen|\bsocket\b|http\.client|subprocess|os\.system|os\.popen"
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


def test_skill_md_carries_three_red_lines():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "不自动提交" in text, "red line 1 (no auto-submit) missing"
    assert "不爬" in text, "red line 2 (no crawling) missing"
    assert "不承诺收录" in text, "red line 3 (no acceptance guarantee) missing"


def test_skill_dir_has_no_readme_or_changelog():
    for path in SKILL_DIR.rglob("*"):
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


def test_openai_yaml_declares_subcommands_and_exit_codes():
    text = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert "name: ai-tool-directory-publisher" in text
    assert "validate" in text and "diff" in text and "status" in text
    assert "0:" in text and "1:" in text and "2:" in text


def test_data_provenance_covers_six_directories():
    text = (SKILL_DIR / "references" / "data-provenance.md").read_text(encoding="utf-8")
    for site in ("futurepedia", "toolify", "theresanaiforthat", "topai.tools"):
        assert site.lower() in text.lower(), "data-provenance missing %s" % site
    assert "以官网为准" in text or "official site is authoritative" in text
