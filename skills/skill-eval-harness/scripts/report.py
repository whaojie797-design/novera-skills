# -*- coding: utf-8 -*-
"""report.py - Finding model and text/JSON rendering for skill-eval-harness.

Deterministic output: findings are sorted by (file, line, rule) before
rendering; identical input always yields byte-identical output.

Dependency direction: report -> (nothing from this skill).
"""

import json
from dataclasses import dataclass, field


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    strength: str
    issue: str
    basis: str


@dataclass
class Stats:
    skill_dir: str
    profile: str
    checks_run: int = 0
    checks_skipped: int = 0
    skipped_ids: list = field(default_factory=list)


def render_text(findings, stats, quiet=False):
    lines = []
    if not quiet:
        lines.append("skill-eval-harness report: %s" % stats.skill_dir)
        lines.append("  profile: %s        checks: %d run / %d skipped"
                     % (stats.profile, stats.checks_run, stats.checks_skipped))
    for f in findings:
        lines.append("[finding] %s:%d  rule=%s  strength=%s"
                     % (f.file, f.line, f.rule, f.strength))
        if not quiet:
            lines.append("  issue:   %s" % f.issue)
            lines.append("  basis:   %s" % f.basis)
    if not quiet:
        for sid in stats.skipped_ids:
            lines.append("note: check %s skipped (not in %s profile)"
                         % (sid, stats.profile))
    noun = "finding" if len(findings) == 1 else "findings"
    exit_code = 1 if findings else 0
    lines.append("summary: %d %s across %d checks. exit code: %d"
                 % (len(findings), noun, stats.checks_run, exit_code))
    return "\n".join(lines)


def render_json(findings, stats):
    return {
        "skill_dir": stats.skill_dir,
        "profile": stats.profile,
        "checks_run": stats.checks_run,
        "checks_skipped": stats.checks_skipped,
        "skipped_ids": list(stats.skipped_ids),
        "summary": {"findings": len(findings)},
        "findings": [
            {
                "file": f.file,
                "line": f.line,
                "rule": f.rule,
                "strength": f.strength,
                "issue": f.issue,
                "basis": f.basis,
            }
            for f in findings
        ],
    }


def render_json_str(findings, stats):
    return json.dumps(render_json(findings, stats), indent=2, sort_keys=True,
                      ensure_ascii=False)
