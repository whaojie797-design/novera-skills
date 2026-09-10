# -*- coding: utf-8 -*-
"""report.py - Finding model and text/JSON rendering for
ai-tool-directory-publisher.

Deterministic output: findings are sorted by (file, line, rule) and
deduplicated before rendering; identical input always yields byte-identical
output.
"""

import json

STRENGTH_RANK = {"unverified": 0, "inferred": 1, "explicit": 2}


class Finding:
    """One audit finding. value/expected are pre-formatted strings produced
    by the checkers (they may embed both sides of a comparison for C1)."""

    __slots__ = ("file", "line", "rule", "strength", "field", "value",
                 "expected")

    def __init__(self, file, line, rule, strength, field, value, expected):
        self.file = file
        self.line = line
        self.rule = rule
        self.strength = strength
        self.field = field
        self.value = value
        self.expected = expected

    def key(self):
        return (self.file, self.line, self.rule, self.field, self.value)


def sort_and_dedupe(findings):
    seen = set()
    out = []
    for f in sorted(findings, key=lambda f: (f.file, f.line, f.rule)):
        k = f.key()
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def render_text(findings, notes=None, quiet=False):
    lines = []
    for f in findings:
        lines.append("[finding] %s:%d  rule=%s  strength=%s"
                     % (f.file, f.line, f.rule, f.strength))
        if not quiet:
            lines.append("  field:    %s" % f.field)
            lines.append("  value:    %s" % f.value)
            lines.append("  expected: %s" % f.expected)
    for n in (notes or []):
        lines.append("note: %s" % n)
    lines.append("%d findings." % len(findings))
    return "\n".join(lines)


def render_json(findings, notes=None):
    return {
        "notes": list(notes or []),
        "summary": {"findings": len(findings)},
        "findings": [
            {
                "file": f.file,
                "line": f.line,
                "rule": f.rule,
                "strength": f.strength,
                "field": f.field,
                "value": f.value,
                "expected": f.expected,
            }
            for f in findings
        ],
    }


def render_json_str(findings, notes=None):
    return json.dumps(render_json(findings, notes), indent=2, sort_keys=True,
                      ensure_ascii=False)
