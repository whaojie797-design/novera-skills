# -*- coding: utf-8 -*-
"""audit.py - CLI entry point for geo-evidence-audit.

Usage:
    python audit.py PATH [--format {text,json}] [--output FILE]
                         [--min-strength {explicit,inferred,unverified}]
                         [--rules R1,R2,...] [--exclude GLOB] [--quiet]

Exit codes:
    0  no findings
    1  findings present (contradictions or unverified claims)
    2  usage or input error (takes priority over 1 and 0)

Offline only: this tool never performs network requests. Coordinate checks
are country-level coarse bounding boxes, NOT precise reverse geocoding.
"""

import argparse
import fnmatch
import os
import sys

from extract import SUPPORTED_EXTENSIONS, extract_signals
from report import STRENGTH_RANK, render_json_str, render_text
from rules import run_checks

ALL_RULES = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]

PROG = "geo-evidence-audit"


def _norm_path(path: str) -> str:
    """Normalize to forward slashes for deterministic cross-platform output."""
    return path.replace("\\", "/")


def _error(msg: str) -> int:
    sys.stderr.write("%s: error: %s\n" % (PROG, msg))
    return 2


def _iter_files(target, exclude_globs):
    """Yield (abs_path, rel_path_display) for supported files.

    Returns (files, skipped_count) semantics via two lists.
    """
    files = []
    skipped = 0
    if os.path.isfile(target):
        ext = os.path.splitext(target)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            files.append(target)
        return files, 0
    for root, _dirs, names in os.walk(target):
        for name in sorted(names):
            full = os.path.join(root, name)
            rel = _norm_path(os.path.relpath(full, target))
            ext = os.path.splitext(name)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                skipped += 1
                continue
            if any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(name, g)
                   for g in exclude_globs):
                continue
            files.append(full)
    return files, skipped


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="audit.py",
        description="Offline auditor for geographic claims in text assets.")
    parser.add_argument("path", help="file or directory (directories are scanned recursively)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="report format (default: text)")
    parser.add_argument("--output", default=None,
                        help="write report to FILE instead of stdout")
    parser.add_argument("--min-strength", choices=["explicit", "inferred", "unverified"],
                        default="unverified",
                        help="report only findings at or above this evidence strength "
                             "(default: unverified = full report)")
    parser.add_argument("--rules", default=None,
                        help="comma-separated rule ids to run, e.g. R1,R4 (default: all)")
    parser.add_argument("--exclude", action="append", default=[],
                        help="glob pattern to exclude files in directory mode "
                             "(repeatable, e.g. --exclude '*_test.*')")
    parser.add_argument("--quiet", action="store_true",
                        help="print one summary line per finding and the count only")
    return parser


def main(argv):
    parser = _build_parser()
    args = parser.parse_args(argv)

    # --- exit code 2: input errors (priority over 1 and 0) -----------------
    target = args.path
    if not os.path.exists(target):
        return _error("path does not exist: %s" % target)

    rules_filter = None
    if args.rules:
        rules_filter = set()
        for part in args.rules.split(","):
            part = part.strip().upper()
            if not part:
                continue
            if part not in ALL_RULES:
                return _error("unknown rule id: %s (valid: %s)"
                              % (part, ",".join(ALL_RULES)))
            rules_filter.add(part)

    if os.path.isdir(target):
        files, skipped = _iter_files(target, args.exclude)
        if not files:
            return _error(
                "no auditable files under %s (supported extensions: %s)"
                % (target, " ".join(sorted(SUPPORTED_EXTENSIONS))))
        dir_mode = True
        base = target
    else:
        files, skipped = _iter_files(target, args.exclude)
        if not files:
            return _error(
                "unsupported file type: %s (supported extensions: %s)"
                % (target, " ".join(sorted(SUPPORTED_EXTENSIONS))))
        dir_mode = False
        base = os.path.dirname(target) or "."

    notes = []
    if skipped:
        notes.append("skipped %d file(s) with unsupported extensions" % skipped)

    # --- extract + cross-check ---------------------------------------------
    files_signals = {}
    for full in files:
        display = _norm_path(os.path.relpath(full, base)) if dir_mode else \
            _norm_path(os.path.basename(full))
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            return _error("cannot read %s: %s" % (full, exc))
        files_signals[display] = extract_signals(text)

    findings = run_checks(files_signals, rules_filter or set(ALL_RULES),
                          dir_mode=dir_mode)

    # --- min-strength filter (lower bound on evidence strength) ------------
    floor = STRENGTH_RANK[args.min_strength]
    findings = [f for f in findings if STRENGTH_RANK.get(f.strength, 0) >= floor]

    # --- render -------------------------------------------------------------
    if args.format == "json":
        report = render_json_str(findings, notes)
    else:
        report = render_text(findings, notes, quiet=args.quiet)

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
