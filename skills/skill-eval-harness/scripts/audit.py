# -*- coding: utf-8 -*-
"""audit.py - CLI entry point for skill-eval-harness.

Usage:
    python audit.py SKILL_DIR [--profile {minimal,novera}] [--only E1,E2,...]
                              [--format {text,json}] [--output FILE]
                              [--quiet]

Exit codes:
    0  all checks passed
    1  findings present
    2  usage or input error (missing dir, no SKILL.md, bad args); 2 > 1 > 0

Static evaluation only: this tool never executes the evaluated skill's
scripts, never initiates network requests, and never assigns behavioral
verdicts (malice analysis is skill-sentry's scope, provenance is
skill-supply-chain-audit's scope). Findings are structure/quality facts.
"""

import argparse
import os
import sys

from checkers import run_checks
from eval_rules import CHECKS
from report import render_json_str, render_text
from skparse import parse_skill_md

PROG = "skill-eval-harness"


def _error(msg):
    sys.stderr.write("%s: error: %s\n" % (PROG, msg))
    return 2


def main(argv):
    parser = argparse.ArgumentParser(
        prog="audit.py",
        description="Offline structural evaluator for Agent Skill packages.")
    parser.add_argument("skill_dir",
                        help="skill package directory (must contain SKILL.md)")
    parser.add_argument("--profile", choices=["minimal", "novera"],
                        default="novera",
                        help="evaluation profile (default: novera with "
                             "exact 8+4+1 trigger inventory)")
    parser.add_argument("--only", default=None,
                        help="comma-separated check ids to run, e.g. E1,E5 "
                             "(default: all checks of the profile)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output", default=None,
                        help="write report to FILE instead of stdout")
    parser.add_argument("--quiet", action="store_true",
                        help="print finding summary lines and count only")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.skill_dir):
        return _error("skill directory does not exist: %s" % args.skill_dir)
    skill_md = os.path.join(args.skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return _error("no SKILL.md in %s (not a skill package)" %
                      args.skill_dir)

    only_ids = None
    if args.only:
        only_ids = []
        for part in args.only.split(","):
            part = part.strip().upper()
            if not part:
                continue
            if part not in CHECKS:
                return _error("unknown check id: %s (valid: %s)"
                              % (part, ",".join(sorted(CHECKS))))
            only_ids.append(part)

    try:
        with open(skill_md, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        return _error("cannot read %s: %s" % (skill_md, exc))

    doc = parse_skill_md(text, skill_md)
    findings, stats = run_checks(doc, args.skill_dir, args.profile, only_ids)

    if args.format == "json":
        report = render_json_str(findings, stats)
    else:
        report = render_text(findings, stats, quiet=args.quiet)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(report + "\n")
        except OSError as exc:
            return _error("cannot write %s: %s" % (args.output, exc))
    else:
        sys.stdout.write(report + "\n")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
