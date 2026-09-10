# -*- coding: utf-8 -*-
"""report.py - Finding model and text/JSON rendering.

Deterministic output: findings sorted by (file, line, rule); identical
input always yields byte-identical output. Inventory items are rendered
as informational lines ("inventory item, not a finding") and never affect
the exit code (design 2.2).
"""

import json
from dataclasses import dataclass, field


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    severity: str        # high | medium | low | info
    strength: str        # explicit | inferred
    signal: str
    basis: str


@dataclass
class Inventory:
    """Reference-surface inventory: informational, not findings (design 2.2)."""
    items: list = field(default_factory=list)   # (file, line, url, kind)
    header: str = ("inventory != risk; endpoint safety is out of scope "
                   "for this skill (runtime behavior is skill-sentry's)")


def render_text(findings, inventory=None, warnings=None, title=""):
    lines = []
    if title:
        lines.append("skill-supply-chain-audit report: %s" % title)
    for w in (warnings or []):
        lines.append("warning: %s" % w)
    for f in findings:
        lines.append("[finding] %s:%d  rule=%s  strength=%s"
                     % (f.file, f.line, f.rule, f.strength))
        lines.append("  signal:   %s" % f.signal)
        lines.append("  basis:    %s" % f.basis)
    if inventory is not None and inventory.items:
        lines.append("inventory: %d external endpoint(s) listed below "
                     "(inventory items, not findings)" % len(inventory.items))
        for file, line, url, kind in inventory.items:
            lines.append("  [inventory] %s:%d  %s  (%s)"
                         % (file, line, url, kind))
        lines.append("note: %s" % inventory.header)
    noun = "finding" if len(findings) == 1 else "findings"
    exit_code = 1 if findings else 0
    lines.append("summary: %d %s. exit code: %d"
                 % (len(findings), noun, exit_code))
    return "\n".join(lines)


def render_json(findings, inventory=None, warnings=None, title=""):
    doc = {
        "tool": "skill-supply-chain-audit",
        "findings": [
            {
                "file": f.file,
                "line": f.line,
                "rule": f.rule,
                "severity": f.severity,
                "strength": f.strength,
                "signal": f.signal,
                "basis": f.basis,
            }
            for f in findings
        ],
        "summary": {"findings": len(findings)},
    }
    if title:
        doc["subject"] = title
    if warnings:
        doc["warnings"] = list(warnings)
    if inventory is not None:
        doc["inventory"] = {
            "note": inventory.header,
            "items": [
                {"file": file, "line": line, "url": url, "kind": kind}
                for file, line, url, kind in inventory.items
            ],
        }
    return doc


def render_json_str(findings, inventory=None, warnings=None, title=""):
    return json.dumps(render_json(findings, inventory, warnings, title),
                      indent=2, sort_keys=True, ensure_ascii=False)
