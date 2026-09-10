# -*- coding: utf-8 -*-
"""audit.py - CLI entry point for ai-tool-directory-publisher.

Usage:
    python audit.py validate PATH [--directory SLUG] [--include-unverified]
                        [--format {text,json}] [--output FILE]
                        [--exclude GLOB] [--quiet]
    python audit.py diff FILE1 FILE2 [...] [--format {text,json}]
                        [--output FILE] [--quiet]
    python audit.py status TABLE [--format {text,json}] [--output FILE]
                        [--quiet]

Exit codes:
    0  no findings
    1  findings present (validation issues, drift, or status-table problems)
    2  usage or input error (takes priority over 1 and 0)

Offline only: this tool never performs network requests. Directory
requirements come from built-in snapshots that change over time; the
official sites are always authoritative. This tool does NOT auto-submit,
does NOT crawl directory sites, and does NOT guarantee listing acceptance.
"""

import argparse
import csv
import fnmatch
import json
import os
import sys

from checkers import StatusRow, run_diff, run_status, run_validate
from directory_data import DIRECTORIES
from listing import parse_listing
from report import render_json_str, render_text, sort_and_dedupe

PROG = "ai-tool-directory-publisher"

LISTING_EXTENSIONS = (".json", ".yaml", ".yml", ".md", ".markdown", ".txt")


def _error(msg):
    sys.stderr.write("%s: error: %s\n" % (PROG, msg))
    return 2


def _emit(args, findings, notes):
    findings = sort_and_dedupe(findings)
    if args.format == "json":
        report = render_json_str(findings, notes)
    else:
        report = render_text(findings, notes, quiet=args.quiet)
    if getattr(args, "output", None):
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(report + "\n")
        except OSError as exc:
            return _error("cannot write %s: %s" % (args.output, exc))
    else:
        sys.stdout.write(report + "\n")
    return 1 if findings else 0


# ---------------------------------------------------------------------------
# Directory resolution


def _resolve_slugs(path, listing):
    """Directory slugs for a listing: explicit `directory` field first, then
    filename tokens. Empty list means "no hint" (validate against all
    verified snapshots and deduplicate identical findings)."""
    slugs = []
    fv = listing.fields.get("directory")
    if fv is not None and isinstance(fv.value, str):
        token = fv.value.strip().lower()
        if token in DIRECTORIES:
            slugs.append(token)
    if not slugs:
        base = os.path.basename(path).lower()
        for slug, spec in sorted(DIRECTORIES.items()):
            if any(tok in base for tok in spec.file_tokens):
                slugs.append(slug)
    return slugs


def _collect_listing_files(target, exclude_globs):
    files = []
    skipped_ext = 0
    if os.path.isfile(target):
        if target.lower().endswith(LISTING_EXTENSIONS):
            files.append(target)
        return files, 0
    for root, _dirs, names in os.walk(target):
        for name in sorted(names):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, target).replace("\\", "/")
            if not name.lower().endswith(LISTING_EXTENSIONS):
                skipped_ext += 1
                continue
            if any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(name, g)
                   for g in exclude_globs):
                continue
            files.append(full)
    return files, skipped_ext


def _load_listing(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        return None, "cannot read %s: %s" % (path, exc)
    return parse_listing(text, path), None


# ---------------------------------------------------------------------------
# Subcommand: validate


def cmd_validate(args):
    target = args.path
    if not os.path.exists(target):
        return _error("path does not exist: %s" % target)
    if args.directory and args.directory not in DIRECTORIES:
        return _error("unknown directory slug: %s (valid: %s)"
                      % (args.directory, ",".join(sorted(DIRECTORIES))))

    files, skipped_ext = _collect_listing_files(target, args.exclude)
    notes = []
    listings = []
    unstructured = 0
    empty_single = False
    for path in files:
        listing, err = _load_listing(path)
        if err:
            return _error(err)
        if listing is None:
            if os.path.isfile(target):
                if not _read_if_empty(path):
                    return _error("no listing structure found in %s" % path)
                empty_single = True  # empty file: legal input, nothing to audit
                continue
            unstructured += 1
            continue
        listings.append(listing)
    if empty_single:
        return _emit(args, [], notes)
    if not listings:
        return _error("no listing structure found in input: %s" % target)
    if unstructured:
        notes.append("skipped %d file(s) without recognizable listing "
                     "structure" % unstructured)
    if skipped_ext:
        notes.append("skipped %d file(s) with unsupported extensions"
                     % skipped_ext)

    findings = []
    for listing in listings:
        display = _display(listing.path, target)
        listing.path = display
        slugs = _resolve_slugs(display, listing)
        if args.directory:
            slugs = [args.directory]
        if not slugs:
            slugs = sorted(s for s, spec in DIRECTORIES.items()
                           if spec.verified)
            multi = True
        else:
            multi = len(slugs) > 1
        seen_in_file = set()
        for slug in slugs:
            spec = DIRECTORIES[slug]
            for f in run_validate(listing, spec, args.include_unverified):
                # identical findings across directories (shared baseline)
                # collapse to one, anchored at the alphabetically first slug
                k = (f.line, f.rule, f.field, f.value)
                if multi and k in seen_in_file:
                    continue
                seen_in_file.add(k)
                findings.append(f)
    if not args.include_unverified:
        unverified = [s for s, spec in sorted(DIRECTORIES.items())
                      if not spec.verified]
        if unverified:
            notes.append("unverified directory snapshots skipped: %s "
                         "(use --include-unverified)" % ",".join(unverified))
    return _emit(args, findings, notes)


def _read_if_empty(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return not fh.read().strip()
    except OSError:
        return False


def _display(path, target):
    if os.path.isdir(target):
        return os.path.relpath(path, target).replace("\\", "/")
    return os.path.basename(path)


# ---------------------------------------------------------------------------
# Subcommand: diff


def cmd_diff(args):
    if len(args.files) < 2:
        return _error("diff needs at least 2 listing files, got %d"
                      % len(args.files))
    listings = []
    for path in args.files:
        if not os.path.exists(path):
            return _error("path does not exist: %s" % path)
        listing, err = _load_listing(path)
        if err:
            return _error(err)
        if listing is None:
            return _error("no listing structure found in %s" % path)
        listing.path = path.replace("\\", "/")
        listings.append(listing)
    findings = run_diff(listings)
    return _emit(args, findings, [])


# ---------------------------------------------------------------------------
# Subcommand: status


def _load_status_rows(path):
    if not os.path.exists(path):
        return None, "path does not exist: %s" % path
    if path.lower().endswith(".csv"):
        try:
            with open(path, "r", encoding="utf-8-sig",
                      errors="replace", newline="") as fh:
                reader = csv.DictReader(fh)
                rows = []
                for rec in reader:
                    rows.append(StatusRow(
                        tool=(rec.get("tool") or "").strip(),
                        directory=(rec.get("directory") or "").strip(),
                        status=(rec.get("status") or "").strip(),
                        date=(rec.get("date") or "").strip(),
                        notes=(rec.get("notes") or "").strip(),
                        line=reader.line_num,
                        source=path.replace("\\", "/"),
                    ))
        except OSError as exc:
            return None, "cannot read %s: %s" % (path, exc)
        return rows, None
    if path.lower().endswith(".json"):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            return None, "cannot parse %s: %s" % (path, exc)
        if not isinstance(data, list):
            return None, "status JSON must be a list of row objects"
        rows = []
        for idx, rec in enumerate(data, start=1):
            if not isinstance(rec, dict):
                return None, "status JSON row %d is not an object" % idx
            rows.append(StatusRow(
                tool=str(rec.get("tool") or "").strip(),
                directory=str(rec.get("directory") or "").strip(),
                status=str(rec.get("status") or "").strip(),
                date=str(rec.get("date") or "").strip(),
                notes=str(rec.get("notes") or "").strip(),
                line=idx,
                source=path.replace("\\", "/"),
            ))
        return rows, None
    return None, ("unsupported status table format: %s (supported: .csv, "
                  ".json)" % path)


def cmd_status(args):
    rows, err = _load_status_rows(args.table)
    if err:
        return _error(err)
    if not rows:
        return _error("status table is empty: %s" % args.table)
    findings = run_status(rows, listing_paths=None)
    return _emit(args, findings, [])


# ---------------------------------------------------------------------------
# Parser


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="audit.py",
        description="Offline auditor for AI tool directory submission "
                    "materials (validate / diff / status).")
    sub = parser.add_subparsers(dest="command")

    p_validate = sub.add_parser(
        "validate", help="validate listing materials against directory "
                         "requirement snapshots")
    p_validate.add_argument("path", help="listing file or directory (a "
                                         "directory is one submission pack)")
    p_validate.add_argument("--directory", default=None,
                            help="only validate against this directory slug "
                                 "(default: all verified snapshots)")
    p_validate.add_argument("--include-unverified", action="store_true",
                            help="also run snapshots not verified against "
                                 "official pages (findings labelled "
                                 "unverified)")
    p_validate.add_argument("--format", choices=["text", "json"],
                            default="text")
    p_validate.add_argument("--output", default=None)
    p_validate.add_argument("--exclude", action="append", default=[])
    p_validate.add_argument("--quiet", action="store_true")

    p_diff = sub.add_parser(
        "diff", help="compare the same tool's listings across directories "
                     "(name/url/pricing/version anchors)")
    p_diff.add_argument("files", nargs="+", help="2+ listing files")
    p_diff.add_argument("--format", choices=["text", "json"], default="text")
    p_diff.add_argument("--output", default=None)
    p_diff.add_argument("--quiet", action="store_true")

    p_status = sub.add_parser(
        "status", help="validate a submission status table (CSV/JSON)")
    p_status.add_argument("table", help="status table file (.csv or .json)")
    p_status.add_argument("--format", choices=["text", "json"], default="text")
    p_status.add_argument("--output", default=None)
    p_status.add_argument("--quiet", action="store_true")
    return parser


def main(argv):
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_usage(sys.stderr)
        return _error("a subcommand is required: validate | diff | status")
    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "diff":
        return cmd_diff(args)
    return cmd_status(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
