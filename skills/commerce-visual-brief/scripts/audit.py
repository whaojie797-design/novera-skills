# -*- coding: utf-8 -*-
"""audit.py - CLI entry for commerce-visual-brief.

Subcommands:
  validate  run V1-V10 over briefs (V6-V9 only with --platform)
  inventory list image placements + spec declarations (informational,
            always exits 0)

Exit codes (2 > 1 > 0):
  0  clean (validate: no findings; inventory: always)
  1  validate found >= 1 finding
  2  usage error (no/unknown subcommand, bad --platform slug, missing path)
     or no brief structure found in the scanned files (uniform: an empty
     file is "no brief structure" too, exit 2)

Options:
  --platform SLUG        enable V6-V9 against a platform snapshot
  --include-unverified   also annotate specs on UNVERIFIED platform entries
                         (honest "not checkable" findings; never fabricated)
  --format text|json     deterministic renderers (default text)
  --output PATH          write the report to PATH (UTF-8, LF); stdout silent
  --exclude GLOB         skip files whose relpath or basename matches
                         (repeatable; matches scanned files only)
  --quiet                no stdout (exit code still communicates)

Determinism: same inputs + same flags => byte-identical output.
All offline; standard library only; Python 3.9+.
"""

import argparse
import fnmatch
import os
import sys

import briefparse
import checkers
import report
from platform_specs import get_platform

USAGE_EXIT = 2


def _eprint(msg):
    sys.stderr.write(msg + "\n")


def build_parser():
    p = argparse.ArgumentParser(
        prog="audit.py",
        description="Validate commerce visual briefs against the novera "
                    "baseline (V1-V10) and list image inventories.")
    sub = p.add_subparsers(dest="command")
    for name in ("validate", "inventory"):
        sp = sub.add_parser(name)
        sp.add_argument("paths", nargs="+",
                        help="brief files or directories to scan")
        sp.add_argument("--platform", default=None, metavar="SLUG",
                        help="platform snapshot for V6-V9 "
                             "(e.g. amazon; default: off, V6-V9 skipped)")
        sp.add_argument("--include-unverified", action="store_true",
                        help="annotate specs on unverified platform "
                             "snapshots instead of silently skipping")
        sp.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
        sp.add_argument("--output", default=None, metavar="PATH",
                        help="write report to PATH (stdout stays silent)")
        sp.add_argument("--exclude", action="append", default=[],
                        metavar="GLOB",
                        help="skip matching files (repeatable)")
        sp.add_argument("--quiet", action="store_true",
                        help="no stdout output")
    return p


def _excluded(relpath, patterns):
    base = os.path.basename(relpath)
    norm = relpath.replace("\\", "/")
    for pat in patterns:
        if fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(base, pat):
            return True
    return False


def collect_files(paths, exclude_patterns):
    """Deterministic file list; (files, missing-path-or-None)."""
    files = []
    for path in paths:
        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            for root, dirs, names in os.walk(path):
                dirs.sort()
                for name in sorted(names):
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, path).replace("\\", "/")
                    if not rel.lower().endswith(briefparse.BRIEF_EXTENSIONS):
                        continue
                    if _excluded(rel, exclude_patterns):
                        continue
                    files.append(full)
        else:
            return [], path
    files = sorted(set(os.path.abspath(f) for f in files))
    return files, None


def load_briefs(files, exclude_patterns, base_dir):
    """Parse files; returns (briefs, skipped). Deterministic order."""
    briefs = []
    skipped = []
    for full in files:
        rel = os.path.relpath(full, base_dir).replace("\\", "/")
        if _excluded(rel, exclude_patterns) or \
                _excluded(os.path.basename(rel), exclude_patterns):
            continue
        try:
            with open(full, "r", encoding="utf-8-sig", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            skipped.append("%s (read error: %s)" % (rel, exc.__class__.__name__))
            continue
        brief = briefparse.parse_brief(text, rel)
        if brief is None:
            skipped.append(rel)
        else:
            briefs.append(brief)
    return briefs, skipped


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command not in ("validate", "inventory"):
        parser.print_usage(sys.stderr)
        _eprint("audit.py: error: a subcommand is required "
                "(validate | inventory)")
        return USAGE_EXIT

    spec = None
    if args.platform is not None:
        spec, err = get_platform(args.platform)
        if err is not None:
            _eprint("audit.py: error: %s" % err)
            return USAGE_EXIT

    files, missing = collect_files(args.paths, args.exclude)
    if missing is not None:
        _eprint("audit.py: error: path not found: %s" % missing)
        return USAGE_EXIT

    base_dir = os.path.abspath(os.path.dirname(args.paths[0])) \
        if len(args.paths) == 1 and os.path.isdir(args.paths[0]) \
        else os.getcwd()
    briefs, skipped = load_briefs(files, args.exclude, base_dir)
    inv = None

    if args.command == "inventory":
        inv = checkers.run_inventory(briefs)
        findings = []
        exit_code = 0          # inventory never affects the exit code
    else:
        findings = checkers.run_validate(
            briefs, spec=spec, include_unverified=args.include_unverified)
        if not briefs:
            exit_code = 2      # no brief structure at all (uniform rule)
        else:
            exit_code = 1 if findings else 0

    meta = {
        "command": args.command,
        "platform_slug": args.platform,
        "platform_verified": bool(spec.verified) if spec else False,
        "snapshot_date": spec.snapshot_date if spec else "",
        "include_unverified": args.include_unverified,
        "briefs_parsed": len(briefs),
        "files_skipped": skipped,
        "exit_code": exit_code,
    }
    if args.format == "json":
        out = report.render_json(findings, inv if args.command == "inventory"
                                 else report.Inventory(), meta)
    else:
        out = report.render_text(findings,
                                 inv if args.command == "inventory"
                                 else report.Inventory(), meta)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
    elif not args.quiet:
        sys.stdout.write(out)
    if exit_code == 2 and args.command == "validate" and not briefs:
        _eprint("audit.py: no brief structure found in scanned files "
                "(%d file(s) scanned)" % len(files))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
