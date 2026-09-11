# -*- coding: utf-8 -*-
"""report.py - Finding/Inventory models + deterministic renderers.

Family conventions:
- Findings carry file:line, a rule id, a strength mark (explicit / inferred /
  unverified / convention), the field or subject, the observed value and the
  expected-why (with default_convention labels and, for V10, DISCLAIMER).
- The inventory is informational: "inventory != risk" and it NEVER affects
  the exit code.
- render_text / render_json are byte-identical for identical inputs: fixed
  field order, sorted keys in JSON, no timestamps, no locale formatting.

Dependency direction: report -> (nothing). checkers imports the
Finding/Inventory models, audit imports the renderers; nothing imports
audit.
"""

import json
from dataclasses import dataclass, field as dc_field
from typing import List, Tuple

VERSION = "commerce-visual-brief v0.1.0"

INVENTORY_NOTE = ("informational: inventory != risk; never affects the "
                  "exit code")

NO_PLATFORM_NOTE = ("no --platform given: V6-V9 image-spec checks skipped "
                    "(pass --platform <slug> to enable)")


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    strength: str        # explicit | inferred | unverified | convention
    field: str
    value: str
    expected: str


@dataclass
class Inventory:
    # each item: (kind, file, line, text)  kind in {"placement", "image-spec"}
    items: List[Tuple[str, str, int, str]] = dc_field(default_factory=list)


def render_text(findings, inventory, meta):
    """Deterministic text report. meta keys: command, platform_slug,
    platform_verified, snapshot_date, include_unverified, briefs_parsed,
    files_skipped (list of str), exit_code."""
    lines = []
    lines.append(VERSION + " " + meta["command"])
    if meta["platform_slug"] is None:
        lines.append("platform: (none) | %s" % NO_PLATFORM_NOTE)
    else:
        lines.append("platform: %s (%s, snapshot %s) | unverified "
                     "included: %s"
                     % (meta["platform_slug"],
                        "verified" if meta["platform_verified"]
                        else "UNVERIFIED",
                        meta["snapshot_date"],
                        "yes" if meta["include_unverified"] else "no"))
    lines.append("briefs parsed: %d | files skipped (no brief structure): %d"
                 % (meta["briefs_parsed"], len(meta["files_skipped"])))
    for skipped in meta["files_skipped"]:
        lines.append("  skipped: %s" % skipped)
    lines.append("findings: %d" % len(findings))
    lines.append("-" * 72)
    for f in findings:
        lines.append("%s %s:%d [%s] %s"
                     % (f.rule, f.file, f.line, f.strength, f.field))
        lines.append("  value: %s" % f.value)
        lines.append("  expected: %s" % f.expected)
    lines.append("-" * 72)
    lines.append("inventory: %d item(s) (%s)" % (len(inventory.items),
                                                 INVENTORY_NOTE))
    for kind, path, line_no, text in inventory.items:
        lines.append("  %s %s:%d %s" % (kind, path, line_no, text))
    lines.append("-" * 72)
    lines.append("summary: %d finding(s). exit code: %d"
                 % (len(findings), meta["exit_code"]))
    return "\n".join(lines) + "\n"


def render_json(findings, inventory, meta):
    """Deterministic JSON report (sorted keys, fixed field order)."""
    platform_obj = None
    if meta["platform_slug"] is not None:
        platform_obj = {
            "slug": meta["platform_slug"],
            "verified": bool(meta["platform_verified"]),
            "snapshot_date": meta["snapshot_date"],
        }
    obj = {
        "version": VERSION,
        "command": meta["command"],
        "platform": platform_obj,
        "note_no_platform": NO_PLATFORM_NOTE if meta["platform_slug"] is None
        else None,
        "include_unverified": bool(meta["include_unverified"]),
        "briefs_parsed": meta["briefs_parsed"],
        "files_skipped": list(meta["files_skipped"]),
        "findings": [
            {
                "rule": f.rule,
                "file": f.file,
                "line": f.line,
                "strength": f.strength,
                "field": f.field,
                "value": f.value,
                "expected": f.expected,
            }
            for f in findings
        ],
        "inventory": {
            "note": INVENTORY_NOTE,
            "items": [
                {"kind": kind, "file": path, "line": line_no, "text": text}
                for kind, path, line_no, text in inventory.items
            ],
        },
        "exit_code": meta["exit_code"],
        "summary": "%d finding(s). exit code: %d"
                   % (len(findings), meta["exit_code"]),
    }
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) \
        + "\n"
