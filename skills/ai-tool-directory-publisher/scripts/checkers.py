# -*- coding: utf-8 -*-
"""checkers.py - Validation, cross-listing diff and status-table checks for
ai-tool-directory-publisher.

Rules:
  V1 missing-required-field     V2 field-length-out-of-range
  V3 invalid-enum               V4 invalid-url
  V5 screenshot-spec-mismatch
  C1 cross-listing-drift (name/url/pricing/version anchors, inferred)
  S1 status-table-integrity

Counter-example protections:
  - pricing case differences ("Free" vs "free") never trigger (V3 normalizes
    case for enum membership; C1 compares case-normalized values)
  - empty features lists are allowed
  - reasonable resubmission rows (rejected -> submitted) in status tables
  - C1 only fires when BOTH sides have the field present and the normalized
    values differ (missing anchors are skipped, prefer no report over false report)

All findings from snapshot-based rules carry the snapshot date and point to
references/data-provenance.md; the official site is always authoritative.

Dependency direction: checkers -> directory_data + report (never audit).
"""

import re
from dataclasses import dataclass
from datetime import date

from directory_data import SNAPSHOT_DATE, SCREENSHOT_SPEC
from report import Finding

STATUS_ENUM = ["draft", "submitted", "under-review", "listed", "rejected"]

_URL_RE = re.compile(r"^https?://\S+$")
_DIMENSIONS_RE = re.compile(r"(\d{2,5})\s*[xX×]\s*(\d{2,5})")
_SPEC_DIMENSIONS_RE = re.compile(r"(\d{2,5})\s*[xX]\s*(\d{2,5})")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_SNAPSHOT_SUFFIX = (" per %s snapshot (%s, see data-provenance; the official "
                    "site is authoritative)")


def _fmt_value(value, is_list):
    if is_list:
        return "%d item(s)" % len(value)
    return '"%s" (%d chars)' % (value, len(value))


def _len_of(field_value):
    if isinstance(field_value.value, list):
        return len(field_value.value)
    return len(field_value.value)


def _is_list(field_value):
    return isinstance(field_value.value, list)


def check_missing_required(listing, spec, strength, findings):
    for fname in sorted(spec.fields):
        fs = spec.fields[fname]
        if fs.required and fname not in listing.fields:
            findings.append(Finding(
                listing.path, 1, "V1", strength, fname, "(missing)",
                "required" + _SNAPSHOT_SUFFIX % (spec.slug, SNAPSHOT_DATE)))


def check_lengths(listing, spec, strength, findings):
    for fname in sorted(spec.fields):
        fs = spec.fields[fname]
        fv = listing.fields.get(fname)
        if fv is None:
            continue
        n = _len_of(fv)
        lo, hi = fs.min_len, fs.max_len
        if lo is None and hi is None:
            continue
        if (lo is not None and n < lo) or (hi is not None and n > hi):
            bound = ">=%d" % lo if hi is None else (
                "<=%d" % hi if lo is None else "%d..%d" % (lo, hi))
            findings.append(Finding(
                listing.path, fv.line, "V2", strength, fname,
                _fmt_value(fv.value, _is_list(fv)),
                "%s chars%s" % (bound, _SNAPSHOT_SUFFIX % (spec.slug,
                                                           SNAPSHOT_DATE))))


def check_enums(listing, spec, strength, findings):
    for fname in sorted(spec.fields):
        fs = spec.fields[fname]
        fv = listing.fields.get(fname)
        if fv is None or fs.enum is None or _is_list(fv):
            continue
        # pricing/category enums match case-insensitively ("Free" == "free")
        if str(fv.value).strip().lower() not in [e.lower() for e in fs.enum]:
            findings.append(Finding(
                listing.path, fv.line, "V3", strength, fname,
                '"%s"' % fv.value,
                "one of %s%s" % ("/".join(fs.enum),
                                 _SNAPSHOT_SUFFIX % (spec.slug, SNAPSHOT_DATE))))


def check_url(listing, spec, strength, findings):
    fv = listing.fields.get("url")
    if fv is None or _is_list(fv):
        return
    url = str(fv.value).strip()
    if not url or not _URL_RE.match(url) or " " in url:
        findings.append(Finding(
            listing.path, fv.line, "V4", "explicit", "url",
            '"%s"' % url,
            "absolute http(s) URL with a scheme and no spaces "
            "(generic rule, no snapshot dependency)"))


def check_screenshot(listing, spec, strength, findings):
    fv = listing.fields.get("screenshot")
    if fv is None or _is_list(fv):
        return
    value = str(fv.value)
    m = _DIMENSIONS_RE.search(value)
    if m is None:
        return  # no parseable dimensions: never flag (prefer no report)
    spec_m = _SPEC_DIMENSIONS_RE.search(SCREENSHOT_SPEC)
    min_w, min_h = int(spec_m.group(1)), int(spec_m.group(2))
    w, h = int(m.group(1)), int(m.group(2))
    if w < min_w or h < min_h:
        findings.append(Finding(
            listing.path, fv.line, "V5", strength, "screenshot",
            '"%s" (%dx%d)' % (value, w, h),
            "%s%s" % (SCREENSHOT_SPEC,
                      _SNAPSHOT_SUFFIX % (spec.slug, SNAPSHOT_DATE))))


def run_validate(listing, spec, include_unverified=False):
    """Validate one listing against one directory snapshot.

    Unverified snapshots are skipped unless include_unverified is set; their
    findings carry strength=unverified. Returns findings for this pair."""
    if not spec.verified and not include_unverified:
        return []
    strength = "explicit" if spec.verified else "unverified"
    findings = []
    check_missing_required(listing, spec, strength, findings)
    check_lengths(listing, spec, strength, findings)
    check_enums(listing, spec, strength, findings)
    check_url(listing, spec, strength, findings)
    check_screenshot(listing, spec, strength, findings)
    return findings


# ---------------------------------------------------------------------------
# C1 cross-listing drift


_ANCHORS = ["name", "url", "pricing", "version"]


def _normalize(anchor, value):
    v = str(value).strip()
    if anchor == "pricing":
        return v.lower()
    if anchor == "url":
        return v.rstrip("/")
    return v


def run_diff(listings):
    """Compare name/url/pricing/version anchors across listings. Findings are
    anchored at each diverging listing and cite the base listing."""
    findings = []
    ordered = sorted(listings, key=lambda l: l.path)
    for anchor in _ANCHORS:
        entries = []
        for l in ordered:
            fv = l.fields.get(anchor)
            if fv is not None and not isinstance(fv.value, list):
                entries.append((l.path, fv.line, str(fv.value)))
        if len(entries) < 2:
            continue
        base_path, base_line, base_value = entries[0]
        base_norm = _normalize(anchor, base_value)
        for path, line, value in entries[1:]:
            if _normalize(anchor, value) != base_norm:
                findings.append(Finding(
                    path, line, "C1", "inferred", anchor,
                    '"%s" (%s:%d)' % (value, path, line),
                    'same %s as %s:%d ("%s") across listings '
                    "(case-insensitive for pricing)" % (anchor, base_path,
                                                        base_line, base_value)))
    return findings


# ---------------------------------------------------------------------------
# S1 status-table integrity


@dataclass
class StatusRow:
    tool: str
    directory: str
    status: str
    date: str
    notes: str
    line: int
    source: str = "(table)"  # status table file path (finding anchor)


def _valid_iso_date(value):
    if not _ISO_DATE_RE.match(value):
        return False
    try:
        date(int(value[0:4]), int(value[5:7]), int(value[8:10]))
        return True
    except ValueError:
        return False


def run_status(rows, listing_paths=None):
    """Check status-table integrity: status enum and ISO 8601 dates.

    listing_paths (optional): when provided, each listing file stem must be
    tracked by at least one row (tool == file stem, case-insensitive)."""
    findings = []
    for row in rows:
        if row.status.strip().lower() not in STATUS_ENUM:
            findings.append(Finding(
                row.source, row.line, "S1", "explicit", "status",
                '"%s"' % row.status,
                "one of %s (generic rule)" % "/".join(STATUS_ENUM)))
        if not row.date or not _valid_iso_date(row.date.strip()):
            findings.append(Finding(
                row.source, row.line, "S1", "explicit", "date",
                '"%s"' % (row.date if row.date else "(missing)"),
                "ISO 8601 date (YYYY-MM-DD) (generic rule)"))
    for path in sorted(listing_paths or []):
        stem = path.replace("\\", "/").rsplit("/", 1)[-1]
        stem = stem.rsplit(".", 1)[0].lower()
        if not any((r.tool or "").strip().lower() == stem for r in rows):
            findings.append(Finding(
                path, 1, "S1", "explicit", "tool", "(not tracked)",
                'status table must contain a row with tool="%s" for this '
                "listing file (generic rule)" % stem))
    return findings
