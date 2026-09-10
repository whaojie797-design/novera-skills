# -*- coding: utf-8 -*-
"""skparse.py - SKILL.md parsing for skill-eval-harness.

Extracts, with line numbers:
  - frontmatter key/value fields (between leading --- fences)
  - total line count
  - trigger / non-trigger numbered-list counts (sections headed with
    "when to use" / "when not to use")
  - end-to-end section count (headings containing "end-to-end")
  - exit-code semantics declaration (a line naming the exit codes and the
    digits 0, 1, 2)
  - whether the text mentions "fixtures" and "file:line" (used by E9/E8)

Dependency direction: skparse -> (nothing from this skill).
"""

import re
from dataclasses import dataclass, field

_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
_NUM_ITEM_RE = re.compile(r"^\s*\d+\.\s+")
_EXIT_LINE_RE = re.compile(r"退出码|exit code", re.IGNORECASE)
_FM_FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_\-]*)\s*:\s*(.*)$")


@dataclass
class Field:
    key: str
    value: str
    line: int


@dataclass
class SkillDoc:
    path: str
    frontmatter: list = field(default_factory=list)  # list[Field]
    frontmatter_found: bool = False
    total_lines: int = 0
    trigger_count: int = 0
    non_trigger_count: int = 0
    e2e_count: int = 0
    exit_code_declared: bool = False
    mentions_fixtures: bool = False
    has_file_line: bool = False


def _parse_frontmatter(lines):
    """Return (fields, found). Frontmatter = leading --- fence block."""
    if not lines or lines[0].strip() != "---":
        return [], False
    fields = []
    for idx in range(1, len(lines)):
        line = lines[idx]
        if line.strip() == "---":
            return fields, True
        m = _FM_FIELD_RE.match(line)
        if m:
            fields.append(Field(m.group(1), m.group(2).strip(), idx + 1))
    return fields, True  # unterminated fence still counts as an attempt


def parse_skill_md(text, path):
    lines = text.splitlines()
    fields, found = _parse_frontmatter(lines)

    trigger_count = 0
    non_trigger_count = 0
    e2e_count = 0
    mode = None
    exit_code_declared = False
    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            t = m.group(1).lower()
            if "when not to use" in t:
                mode = "non"
            elif "when to use" in t:
                mode = "trigger"
            elif "end-to-end" in t:
                e2e_count += 1
                mode = None
            else:
                mode = None
            continue
        if _NUM_ITEM_RE.match(line):
            if mode == "trigger":
                trigger_count += 1
            elif mode == "non":
                non_trigger_count += 1
        if _EXIT_LINE_RE.search(line) and all(
                d in line for d in ("0", "1", "2")):
            exit_code_declared = True

    low = text.lower()
    return SkillDoc(
        path=path,
        frontmatter=fields,
        frontmatter_found=found,
        total_lines=len(lines),
        trigger_count=trigger_count,
        non_trigger_count=non_trigger_count,
        e2e_count=e2e_count,
        exit_code_declared=exit_code_declared,
        mentions_fixtures="fixtures" in low,
        has_file_line="file:line" in low,
    )
