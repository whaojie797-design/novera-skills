# -*- coding: utf-8 -*-
"""listing.py - Listing file parsing for ai-tool-directory-publisher.

Supported inputs (offline, stdlib only):
  - JSON: a flat top-level object with scalar or list-of-scalars values.
  - YAML: hand-written MINIMAL SUBSET parser (no PyYAML): flat "key: value"
    lines, optionally "key:" followed by "- item" list lines, comments and
    blank lines ignored. Anything more complex (nesting, inline dicts,
    anchors) is reported as unsupported via a return of None.
  - Markdown: YAML frontmatter ("---" fenced block at the top) parsed with
    the same minimal subset, plus "- key: value" bullet lines in the body.

parse_listing returns a Listing (fields carry line numbers) or None when the
input has no recognizable listing structure / uses an unsupported structure.
"""

import json
import re
from dataclasses import dataclass, field


@dataclass
class FieldValue:
    value: object  # str for scalars, list[str] for lists
    line: int


@dataclass
class Listing:
    path: str
    fields: dict = field(default_factory=dict)  # field name -> FieldValue


_YAML_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_\-]*)\s*:\s*(.*)$")
_YAML_LIST_ITEM_RE = re.compile(r"^\s+-\s+(.*)$")
_QUOTED_RE = re.compile(r"^(\"(.*)\"|'(.*)')$")


def _clean_scalar(raw):
    raw = raw.strip()
    if not raw:
        return None
    m = _QUOTED_RE.match(raw)
    if m:
        return m.group(2) if m.group(2) is not None else m.group(3)
    # strip trailing comment (only when preceded by whitespace, keep URLs intact)
    if " #" in raw:
        raw = raw.split(" #", 1)[0].rstrip()
    return raw


def _parse_yaml_subset(text, line_offset=0):
    """Parse the minimal YAML subset. Returns dict[str, FieldValue] or None
    when an unsupported structure is encountered."""
    fields = {}
    current_key = None
    for offset, raw_line in enumerate(text.splitlines()):
        lineno = offset + 1 + line_offset
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.strip() == "---":
            continue
        item = _YAML_LIST_ITEM_RE.match(line)
        if item and current_key is not None:
            val = _clean_scalar(item.group(1))
            if val is None:
                return None  # "- " with empty item: unsupported
            if not isinstance(fields[current_key].value, list):
                return None  # scalar followed by list items: unsupported
            fields[current_key].value.append(val)
            continue
        if item:
            return None  # list item before any key: unsupported
        if line.startswith((" ", "\t")):
            return None  # deeper indentation: unsupported nesting
        m = _YAML_KEY_RE.match(line)
        if not m:
            return None  # plain prose: not listing structure in YAML mode
        key = m.group(1).lower()
        rest = m.group(2)
        if rest.strip():
            val = _clean_scalar(rest)
            if val is None:
                return None
            fields[key] = FieldValue(val, lineno)
            current_key = key
        else:
            fields[key] = FieldValue([], lineno)  # possible list follows
            current_key = key
    # keys left with empty lists that never got items stay as empty lists
    return fields


def _parse_json(text, path):
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    lines = text.splitlines()
    fields = {}
    for key, value in data.items():
        if not isinstance(key, str):
            return None
        lineno = 1
        pattern = re.compile(r"\"%s\"\s*:" % re.escape(key))
        for offset, line in enumerate(lines):
            if pattern.search(line):
                lineno = offset + 1
                break
        if isinstance(value, str):
            fields[key.lower()] = FieldValue(value, lineno)
        elif isinstance(value, list) and all(
                isinstance(v, (str, int, float)) for v in value):
            fields[key.lower()] = FieldValue(
                [str(v) for v in value], lineno)
        elif isinstance(value, (int, float, bool)):
            fields[key.lower()] = FieldValue(str(value), lineno)
        else:
            return None  # nested dict / mixed structures: unsupported
    return fields


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)
_MD_BULLET_RE = re.compile(r"^-\s+([A-Za-z][A-Za-z0-9_\-]*)\s*:\s*(.*)$")


def _parse_markdown(text, path):
    fields = {}
    m = _FRONTMATTER_RE.match(text)
    body_start = 0
    if m:
        fm_fields = _parse_yaml_subset(m.group(1), line_offset=0)
        if fm_fields is None:
            return None
        fields.update(fm_fields)
        body_start = m.end()
    for offset, line in enumerate(text[body_start:].splitlines()):
        lineno = offset + 1 + text[:body_start].count("\n")
        bm = _MD_BULLET_RE.match(line)
        if bm:
            key = bm.group(1).lower()
            val = _clean_scalar(bm.group(2))
            if val is None:
                continue
            fields[key] = FieldValue(val, lineno)
    return fields or None


def parse_listing(text, path):
    """Parse listing text. Returns Listing, or None when the input is empty,
    has no listing structure, or uses an unsupported structure."""
    if not text.strip():
        return None  # caller decides: empty file is a legal no-op input
    if path.lower().endswith(".json"):
        fields = _parse_json(text, path)
    elif path.lower().endswith((".yaml", ".yml")):
        fields = _parse_yaml_subset(text)
    elif path.lower().endswith((".md", ".markdown")):
        fields = _parse_markdown(text, path)
    elif path.lower().endswith(".txt"):
        fields = _parse_yaml_subset(text)
        if fields is None:
            fields = _parse_markdown(text, path)
    else:
        return None
    if not fields:
        return None
    return Listing(path=path, fields=fields)
