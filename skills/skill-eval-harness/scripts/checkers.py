# -*- coding: utf-8 -*-
"""checkers.py - E1-E12 check implementations for skill-eval-harness.

Static evaluation only: the evaluated skill's scripts are parsed as AST,
never executed. AST analysis (E5/E6) only looks at real Import/ImportFrom
and Call nodes, so the text "import socket" inside comments or string
literals can never trigger a finding. Local sibling imports (module names
backed by files inside the evaluated scripts/ directory) are allowed by E5.

Dependency direction: checkers -> eval_rules + report (never audit).
"""

import ast
import fnmatch
import os
import re

from eval_rules import (
    BANNED_CALL_ROOTS,
    CHECKS,
    FORBIDDEN_FILE_PATTERNS,
    LINE_BUDGET,
    NOVERA_E2E_COUNT,
    NOVERA_NON_TRIGGER_COUNT,
    NOVERA_TRIGGER_COUNT,
    OS_BANNED_FUNC_PREFIXES,
    PROFILE_CHECKS,
    STDLIB_MODULES,
)
from report import Finding, Stats

_LINE_WORD_RE = re.compile(r"\bline\b", re.IGNORECASE)
_YAML_NAME_RE = re.compile(r"^name\s*:\s*(.+?)\s*$")
_DOTTED_ATTR_RE = None  # built inline via _dotted_name()


def _basis(profile, cid):
    return "%s profile %s (see references/rules.md)" % (profile, cid)


def _finding(file, line, cid, issue, profile):
    return Finding(file, line, cid, "explicit", issue, _basis(profile, cid))


# ---------------------------------------------------------------------------
# SKILL.md checks (E1-E4)


def check_frontmatter(doc, profile, findings):
    if not doc.frontmatter_found:
        findings.append(_finding("SKILL.md", 1, "E1",
                                 "frontmatter missing (no --- fence block)",
                                 profile))
        return
    keys = {f.key.lower() for f in doc.frontmatter}
    for required in ("name", "description"):
        if required not in keys:
            findings.append(_finding(
                "SKILL.md", 1, "E1",
                'frontmatter missing required field "%s"' % required,
                profile))
    for f in doc.frontmatter:
        if f.key.lower() not in ("name", "description"):
            findings.append(_finding(
                "SKILL.md", f.line, "E1",
                'frontmatter contains extra field "%s" (only name and '
                "description are allowed)" % f.key, profile))


def check_line_budget(doc, profile, findings):
    if doc.total_lines >= LINE_BUDGET:
        findings.append(_finding(
            "SKILL.md", 1, "E2",
            "SKILL.md has %d lines (budget: fewer than %d)"
            % (doc.total_lines, LINE_BUDGET), profile))


def check_trigger_inventory(doc, profile, findings):
    if profile == "minimal":
        if doc.trigger_count == 0:
            findings.append(_finding(
                "SKILL.md", 1, "E3",
                "trigger inventory missing (no 'when to use' section with "
                "numbered items)", profile))
        return
    # novera: exact 8 + 4 + 1 (lead ruling on A6: no tolerance)
    mismatches = []
    if doc.trigger_count != NOVERA_TRIGGER_COUNT:
        mismatches.append("triggers=%d (want %d)"
                          % (doc.trigger_count, NOVERA_TRIGGER_COUNT))
    if doc.non_trigger_count != NOVERA_NON_TRIGGER_COUNT:
        mismatches.append("non-triggers=%d (want %d)"
                          % (doc.non_trigger_count, NOVERA_NON_TRIGGER_COUNT))
    if doc.e2e_count != NOVERA_E2E_COUNT:
        mismatches.append("end-to-end=%d (want %d)"
                          % (doc.e2e_count, NOVERA_E2E_COUNT))
    if mismatches:
        findings.append(_finding(
            "SKILL.md", 1, "E3",
            "trigger inventory mismatch: %s" % ", ".join(mismatches),
            profile))


def check_exit_codes(doc, profile, findings):
    if not doc.exit_code_declared:
        findings.append(_finding(
            "SKILL.md", 1, "E4",
            "no exit-code semantics declaration (a line naming the exit "
            "codes with 0, 1 and 2)", profile))


# ---------------------------------------------------------------------------
# scripts checks (E5-E8) -- AST based


def _iter_script_files(skill_dir):
    scripts = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts):
        return []
    out = []
    for root, _dirs, names in os.walk(scripts):
        for name in sorted(names):
            if name.endswith(".py"):
                out.append(os.path.join(root, name))
    return sorted(out)


def _local_module_names(skill_dir):
    scripts = os.path.join(skill_dir, "scripts")
    names = set()
    if os.path.isdir(scripts):
        for entry in os.listdir(scripts):
            if entry.endswith(".py"):
                names.add(entry[:-3])
            elif os.path.isdir(os.path.join(scripts, entry)):
                names.add(entry)
    return names


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _dotted_name(node):
    """Best-effort dotted name of a Call func node (Attribute/Name)."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def check_scripts(doc, skill_dir, profile, active, findings):
    files = _iter_script_files(skill_dir)
    need_ast = ("E5" in active or "E6" in active or "E7" in active)
    trees = {}
    sources = {}
    if need_ast:
        local = _local_module_names(skill_dir)
        allowed = STDLIB_MODULES | local | {"__future__"}
        for path in files:
            rel = os.path.relpath(path, skill_dir).replace("\\", "/")
            try:
                tree = ast.parse(_read(path), mode="exec",
                                 feature_version=(3, 9))
            except SyntaxError as exc:
                if "E7" in active:
                    findings.append(_finding(
                        rel, exc.lineno or 1, "E7",
                        "syntax error: %s" % exc.msg, profile))
                continue
            trees[path] = tree
            sources[path] = rel

            if "E5" in active:
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            top = alias.name.split(".")[0]
                            if top not in allowed:
                                findings.append(_finding(
                                    rel, node.lineno, "E5",
                                    'import "%s" not in stdlib allowlist'
                                    % alias.name, profile))
                    elif isinstance(node, ast.ImportFrom):
                        if node.level > 0 or node.module is None:
                            continue  # relative import inside the package
                        top = node.module.split(".")[0]
                        if top not in allowed:
                            findings.append(_finding(
                                rel, node.lineno, "E5",
                                'import "%s" not in stdlib allowlist'
                                % node.module, profile))

            if "E6" in active:
                # aliases bound from banned modules: `from subprocess import run`
                banned_aliases = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module in \
                            BANNED_CALL_ROOTS:
                        for alias in node.names:
                            banned_aliases.add(alias.asname or alias.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in BANNED_CALL_ROOTS:
                                banned_aliases.add(alias.asname or alias.name)
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    dotted = _dotted_name(node.func)
                    if dotted is None:
                        continue
                    root_hit = any(dotted == r or dotted.startswith(r + ".")
                                   for r in BANNED_CALL_ROOTS)
                    os_hit = (dotted.startswith("os.")
                              and any(dotted[3:].startswith(p)
                                      for p in OS_BANNED_FUNC_PREFIXES))
                    alias_hit = (isinstance(node.func, ast.Name)
                                 and node.func.id in banned_aliases)
                    if root_hit or os_hit or alias_hit:
                        findings.append(_finding(
                            rel, node.lineno, "E6",
                            'network/spawn call "%s" detected (structure '
                            "violation only; no behavior verdict)"
                            % dotted, profile))

    if "E8" in active:
        has_lineage = doc.has_file_line or any(
            _LINE_WORD_RE.search(_read(p)) for p in files)
        if not has_lineage:
            findings.append(_finding(
                "SKILL.md", 1, "E8",
                "no finding-lineage evidence: SKILL.md never mentions "
                "'file:line' and no script carries a line field", profile))


# ---------------------------------------------------------------------------
# fixtures (E9) and structure (E10-E12)


def check_fixtures_contract(doc, skill_dir, profile, findings):
    fixtures_dir = os.path.join(skill_dir, "fixtures")
    if not os.path.isdir(fixtures_dir):
        if doc.mentions_fixtures:
            findings.append(_finding(
                "SKILL.md", 1, "E9",
                "fixtures/ directory missing (SKILL.md references fixtures)",
                profile))
        return
    manifest = os.path.join(fixtures_dir, "MANIFEST.tsv")
    if not os.path.isfile(manifest):
        findings.append(_finding(
            "SKILL.md", 1, "E9",
            "fixtures/MANIFEST.tsv missing (pack has a fixtures/ directory)",
            profile))
        return
    with open(manifest, "r", encoding="utf-8-sig", errors="replace") as fh:
        for lineno, raw in enumerate(fh.read().splitlines(), start=1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                findings.append(_finding(
                    "fixtures/MANIFEST.tsv", lineno, "E9",
                    "manifest line must be <relpath><TAB><expected_exit> "
                    "with exactly 2 columns", profile))
                continue
            relpath, expected = parts[0].strip(), parts[1].strip()
            if expected not in ("0", "1", "2"):
                findings.append(_finding(
                    "fixtures/MANIFEST.tsv", lineno, "E9",
                    "invalid expected_exit %r (must be 0, 1 or 2)"
                    % expected, profile))
            # Two accepted relpath conventions (see references/rules.md E9):
            # a path starting with "fixtures/" is resolved against the skill
            # package root; any other path is resolved against the fixtures/
            # directory itself (bare fixture names).
            if os.path.isabs(relpath) or ".." in relpath.split("/"):
                findings.append(_finding(
                    "fixtures/MANIFEST.tsv", lineno, "E9",
                    'fixture relpath "%s" must stay inside the package'
                    % relpath, profile))
                continue
            norm = relpath.replace("/", os.sep)
            if relpath == "fixtures" or relpath.startswith("fixtures/"):
                target = os.path.join(skill_dir, norm)
            else:
                target = os.path.join(fixtures_dir, norm)
            if not os.path.exists(target):
                findings.append(_finding(
                    "fixtures/MANIFEST.tsv", lineno, "E9",
                    'fixture "%s" missing in package' % relpath, profile))


def check_openai_yaml(doc, skill_dir, profile, findings):
    yaml_path = os.path.join(skill_dir, "agents", "openai.yaml")
    if not os.path.isfile(yaml_path):
        findings.append(_finding(
            "SKILL.md", 1, "E10",
            "agents/openai.yaml missing", profile))
        return
    fm_name = None
    for f in doc.frontmatter:
        if f.key.lower() == "name":
            fm_name = f.value.strip()
    with open(yaml_path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh.read().splitlines(), start=1):
            m = _YAML_NAME_RE.match(line)
            if m:
                yaml_name = m.group(1).strip().strip("\"'")
                if fm_name is not None and yaml_name != fm_name:
                    findings.append(_finding(
                        "agents/openai.yaml", lineno, "E10",
                        'openai.yaml name "%s" does not match SKILL.md '
                        'frontmatter name "%s"' % (yaml_name, fm_name),
                        profile))
                return  # only the first top-level name field counts


def check_references(skill_dir, profile, findings):
    refs = os.path.join(skill_dir, "references")
    if not os.path.isdir(refs):
        findings.append(_finding(
            "SKILL.md", 1, "E11", "references/ directory missing", profile))
        return
    has_files = any(
        len(names) > 0 for _r, _d, names in os.walk(refs))
    if not has_files:
        findings.append(_finding(
            "SKILL.md", 1, "E11", "references/ directory is empty (missing)",
            profile))


def check_forbidden_files(skill_dir, profile, findings):
    fixtures_dir = os.path.abspath(os.path.join(skill_dir, "fixtures"))
    for root, dirs, names in os.walk(skill_dir):
        if os.path.abspath(root) == fixtures_dir:
            # fixtures/ contents are fixture material (design section 7):
            # they carry intentionally broken mini packages and never
            # represent the host skill, so E12 does not scan them.
            dirs[:] = []
            continue
        for name in sorted(names):
            if any(fnmatch.fnmatch(name.lower(), pat)
                   for pat in FORBIDDEN_FILE_PATTERNS):
                rel = os.path.relpath(os.path.join(root, name),
                                      skill_dir).replace("\\", "/")
                findings.append(_finding(
                    rel, 1, "E12",
                    'forbidden file "%s" inside skill package' % name,
                    profile))


# ---------------------------------------------------------------------------
# Entry point


def run_checks(doc, skill_dir, profile, only_ids=None):
    """Run the active checks; returns (findings, stats).

    Without --only: every check eligible for the profile runs; checks whose
    spec excludes the profile are counted as skipped (minimal skips E8).
    With --only: the explicitly selected ids run regardless of profile
    (--only overrides the profile default set, see references/rules.md);
    everything else counts as skipped.
    """
    all_ids = list(CHECKS)
    if only_ids is not None:
        selected = set(only_ids)
    else:
        selected = set(cid for cid in all_ids
                       if profile in CHECKS[cid].profiles)
    active = [cid for cid in all_ids if cid in selected]
    skipped = [cid for cid in all_ids if cid not in selected]
    active_set = set(active)
    findings = []

    if "E1" in active_set:
        check_frontmatter(doc, profile, findings)
    if "E2" in active_set:
        check_line_budget(doc, profile, findings)
    if "E3" in active_set:
        check_trigger_inventory(doc, profile, findings)
    if "E4" in active_set:
        check_exit_codes(doc, profile, findings)
    if active_set & {"E5", "E6", "E7", "E8"}:
        check_scripts(doc, skill_dir, profile, active_set, findings)
    if "E9" in active_set:
        check_fixtures_contract(doc, skill_dir, profile, findings)
    if "E10" in active_set:
        check_openai_yaml(doc, skill_dir, profile, findings)
    if "E11" in active_set:
        check_references(skill_dir, profile, findings)
    if "E12" in active_set:
        check_forbidden_files(skill_dir, profile, findings)

    findings.sort(key=lambda f: (f.file, f.line, f.rule))
    stats = Stats(skill_dir=skill_dir.replace("\\", "/"), profile=profile,
                  checks_run=len(active), checks_skipped=len(skipped),
                  skipped_ids=sorted(skipped))
    return findings, stats
