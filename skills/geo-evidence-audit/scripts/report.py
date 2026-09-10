# -*- coding: utf-8 -*-
"""report.py - Text/JSON report rendering for geo-evidence-audit.

Deterministic output: findings sorted by (file, line, rule) before calling
the renderers; same input always yields byte-identical output.

Dependency direction: report -> (nothing from this skill).
"""

import json


STRENGTH_RANK = {"unverified": 0, "inferred": 1, "explicit": 2}

NOTES_STATIC = [
    "bbox-based checks use approximate country-level bounding boxes; "
    "they are NOT precise reverse geocoding",
    "this tool audits internal consistency only; it does not verify "
    "whether claims are true (unverified does not mean false)",
]


def render_text(findings, notes=None, quiet=False):
    """Plain-text report. quiet=True prints one summary line per finding."""
    lines = []
    for f in findings:
        lines.append(
            "[finding] %s:%d  rule=%s  strength=%s" % (f.file, f.line, f.rule, f.strength))
        if not quiet:
            lines.append("  claimed:  %s" % f.claimed)
            lines.append("  conflict: %s" % f.conflict)
    lines.append("%d findings." % len(findings))
    return "\n".join(lines)


def render_json(findings, notes=None):
    """JSON-serializable dict with findings and notes."""
    all_notes = list(NOTES_STATIC)
    for n in (notes or []):
        if n not in all_notes:
            all_notes.append(n)
    return {
        "notes": all_notes,
        "summary": {"findings": len(findings)},
        "findings": [
            {
                "file": f.file,
                "line": f.line,
                "rule": f.rule,
                "severity": f.severity,
                "strength": f.strength,
                "claimed": f.claimed,
                "conflict": f.conflict,
            }
            for f in findings
        ],
    }


def render_json_str(findings, notes=None):
    return json.dumps(render_json(findings, notes), indent=2, sort_keys=True,
                      ensure_ascii=False)
