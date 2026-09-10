# -*- coding: utf-8 -*-
"""audit.py - CLI entry point for skill-supply-chain-audit.

Usage:
    python audit.py <subcommand> ...

    profile REPO_JSON COMMITS_JSON CONTRIBUTORS_JSON [--releases F]
            [--format {text,json,sarif}] [--output FILE] [--quiet]
    refs SKILL_DIR [--format {text,json,sarif}] [--output FILE] [--quiet]
    chain SKILL_DIR [--against REMOTE_OR_ARCHIVE_TXT]
            [--format {text,json,sarif}] [--output FILE] [--quiet]

Exit codes:
    0  no findings (inventory presence does not affect this)
    1  findings present (risk signals S1-S10)
    2  usage or input error (invalid snapshot JSON, schema violation,
       directory without SKILL.md, bad args, missing subcommand); 2 > 1 > 0

Offline by design: snapshots are user-provided files; nothing is fetched.
No trust score, no maliciousness verdict - signals only.
"""

import argparse
import os
import sys
from datetime import date

import checkers
from report import render_json_str, render_text
from sarif import render_sarif_str
from snapshot import SnapshotError, load_gh_export, minimal_html_text

PROG = "skill-supply-chain-audit"


def _error(msg):
    sys.stderr.write("%s: error: %s\n" % (PROG, msg))
    return 2


def _emit(findings, inventory, warnings, title, args):
    if args.format == "json":
        out = render_json_str(findings, inventory, warnings, title)
    elif args.format == "sarif":
        # SARIF carries findings only; inventory/warnings stay in text/json.
        out = render_sarif_str(findings, PROG, base_dir=os.getcwd())
    else:
        out = render_text(findings, inventory, warnings, title)
        if args.quiet:
            out = _quiet_text(findings, title)
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(out + "\n")
        except OSError as exc:
            return _error("cannot write %s: %s" % (args.output, exc))
    else:
        sys.stdout.write(out + "\n")
    return 1 if findings else 0


def _quiet_text(findings, title):
    lines = []
    if title:
        lines.append("skill-supply-chain-audit report: %s" % title)
    for f in findings:
        lines.append("[finding] %s:%d  rule=%s  strength=%s"
                     % (f.file, f.line, f.rule, f.strength))
    noun = "finding" if len(findings) == 1 else "findings"
    lines.append("summary: %d %s. exit code: %d"
                 % (len(findings), noun, 1 if findings else 0))
    return "\n".join(lines)


def _add_common(p):
    p.add_argument("--format", choices=["text", "json", "sarif"],
                   default="text")
    p.add_argument("--output", default=None,
                   help="write report to FILE instead of stdout")
    p.add_argument("--quiet", action="store_true",
                   help="print finding summary lines and count only")


def cmd_profile(args):
    try:
        snap = load_gh_export(args.repo_json, args.commits_json,
                              args.contributors_json,
                              releases_path=args.releases_json)
    except SnapshotError as exc:
        return _error(str(exc))
    findings, warnings = checkers.run_profile(snap, date.today())
    return _emit(findings, None, warnings, args.repo_json, args)


def _require_skill_dir(args):
    if not os.path.isdir(args.skill_dir):
        return _error("skill directory does not exist: %s" % args.skill_dir)
    if not os.path.isfile(os.path.join(args.skill_dir, "SKILL.md")):
        return _error("no SKILL.md in %s (not a skill package)"
                      % args.skill_dir)
    return None


def cmd_refs(args):
    err = _require_skill_dir(args)
    if err is not None:
        return err
    findings, inventory = checkers.run_refs(args.skill_dir)
    return _emit(findings, inventory, None, args.skill_dir, args)


def cmd_chain(args):
    err = _require_skill_dir(args)
    if err is not None:
        return err
    against_text = None
    if args.against:
        if not os.path.isfile(args.against):
            return _error("--against file does not exist: %s" % args.against)
        try:
            with open(args.against, "r", encoding="utf-8-sig",
                      errors="replace") as fh:
                against_text = fh.read()
        except OSError as exc:
            return _error("cannot read %s: %s" % (args.against, exc))
        # marketplace HTML archive input: minimal text extraction (ruling 3)
        if args.against.lower().endswith((".html", ".htm")):
            against_text = minimal_html_text(against_text)
    findings, warnings = checkers.run_chain(args.skill_dir, against_text)
    return _emit(findings, None, warnings, args.skill_dir, args)


def main(argv):
    parser = argparse.ArgumentParser(
        prog="audit.py",
        description="Offline origin-side supply-chain profiler for Agent "
                    "Skill packages (snapshots only, never fetches).")
    sub = parser.add_subparsers(dest="subcommand")

    p_profile = sub.add_parser(
        "profile", help="repository health signals from a gh api export")
    p_profile.add_argument("repo_json")
    p_profile.add_argument("commits_json")
    p_profile.add_argument("contributors_json")
    p_profile.add_argument("--releases", dest="releases_json", default=None)
    _add_common(p_profile)
    p_profile.set_defaults(func=cmd_profile)

    p_refs = sub.add_parser(
        "refs", help="reference-surface inventory plus S6/S7 findings")
    p_refs.add_argument("skill_dir")
    _add_common(p_refs)
    p_refs.set_defaults(func=cmd_refs)

    p_chain = sub.add_parser(
        "chain", help="distribution-chain risks (S8-S10)")
    p_chain.add_argument("skill_dir")
    p_chain.add_argument("--against", default=None,
                         help="optional remote.txt / HTML archive for "
                              "origin comparison")
    _add_common(p_chain)
    p_chain.set_defaults(func=cmd_chain)

    args = parser.parse_args(argv)
    if not getattr(args, "subcommand", None):
        return _error("a subcommand is required "
                      "(profile | refs | chain)")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
