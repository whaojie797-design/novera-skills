# -*- coding: utf-8 -*-
"""rules.py - Cross-signal consistency checks (R1-R7) for geo-evidence-audit.

Rules:
  R1 phone-vs-country      R2 tz-vs-place        R3 currency-vs-country
  R4 coord-vs-country      R5 locale-vs-place    R6 map-vs-place
  R7 unverified-claim (fallback)

All R1-R6 findings are strength "inferred" and carry a reasoning chain in the
conflict text. R7 findings are strength "unverified" (info severity).

Counter-example protections (do NOT trigger):
  - eurozone members paying in EUR (R3)
  - multi-timezone countries: any listed offset matching (R2)
  - bilingual city names pointing at the same country
  - same file / directory with each office's own signals self-consistent

Dependency direction: rules -> geo_data (never extract/audit/report).
"""

import re
from dataclasses import dataclass

from geo_data import (
    COUNTRIES,
    COUNTRY_ALIASES,
    CURRENCY_SYMBOLS,
    EUROZONE_MEMBERS,
    IANA_TZ_COUNTRY,
)

WINDOW = 6  # kept for reference: signals are paired to the NEAREST place
            # mention (see _pair_signals); window no longer gates pairing


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    strength: str
    claimed: str
    conflict: str
    severity: str


def _build_place_index():
    index = {}
    for iso2, info in COUNTRIES.items():
        for name in list(info.cities_en) + [info.name_en]:
            index.setdefault(name.lower(), iso2)
    for alias, iso2 in COUNTRY_ALIASES.items():
        index.setdefault(alias.lower(), iso2)
    return index


_PLACE_INDEX = _build_place_index()

_BBOX_TOL = 0.01
_OFFSET_TOL = 0.01


def _country_of_place(signal):
    return signal.value.split("|")[-1]


def _place_name(signal):
    return signal.value.split("|")[0]


def _pair_signals(signals):
    """Assign every non-place signal to its nearest place mention.

    Returns claims: dict {(name, country): {"lines": [..], "signals": [..]}}
    where "lines" are the mention lines of the claim and "signals" the
    non-place signals nearest-assigned to any mention of it. Tie-break:
    earlier line, then earlier column. This keeps per-record signals
    (JSON/CSV rows) isolated from neighbouring records.
    """
    places = [s for s in signals if s.category == "place"]
    claims = {}
    for p in places:
        key = (_place_name(p), _country_of_place(p))
        claims.setdefault(key, {"lines": [], "signals": []})
        claims[key]["lines"].append(p.line)
    for s in signals:
        if s.category == "place" or not places:
            continue
        best = min(places, key=lambda p: (abs(p.line - s.line), p.line, p.col))
        key = (_place_name(best), _country_of_place(best))
        claims[key]["signals"].append(s)
    return claims


def _currency_codes(signal):
    """ISO 4217 codes a currency signal may stand for."""
    val = signal.value
    if val in CURRENCY_SYMBOLS:
        return set(CURRENCY_SYMBOLS[val])
    return {val}


def _currency_consistent(iso2, codes):
    info = COUNTRIES.get(iso2)
    if info is None:
        return True  # unknown country: never flag (lenient)
    if codes & set(info.currencies):
        return True
    if "EUR" in codes and iso2 in EUROZONE_MEMBERS:
        return True
    return False


def _in_bbox(iso2, lat, lon):
    info = COUNTRIES.get(iso2)
    if info is None or not info.bbox:
        return True  # unknown: lenient
    min_lon, min_lat, max_lon, max_lat = info.bbox
    return (min_lon - _BBOX_TOL <= lon <= max_lon + _BBOX_TOL
            and min_lat - _BBOX_TOL <= lat <= max_lat + _BBOX_TOL)


def _offsets_consistent(iso2, offset):
    info = COUNTRIES.get(iso2)
    if info is None or not info.tz_offsets:
        return True
    return any(abs(offset - o) < _OFFSET_TOL for o in info.tz_offsets)


def _tz_offset(signal):
    """UTC offset float from a timezone signal value, or None."""
    val = signal.value
    if "|" in val:
        try:
            return float(val.rsplit("|", 1)[1])
        except ValueError:
            return None
    m = re.match(r"^UTC([+\-][\d.]+)$", val)
    if m:
        return float(m.group(1))
    return None


def _tz_country(signal):
    """ISO2 country of an IANA zone signal, or None for raw offsets."""
    val = signal.value
    if "|" not in val:
        return None
    zone = val.rsplit("|", 1)[0]
    return IANA_TZ_COUNTRY.get(zone)


def _fmt_offset(x):
    return "UTC%+g" % x


def _dedupe(findings):
    # Same claim + same conflict reported from multiple mention lines of the
    # identical claim text (e.g. title + body) counts once, at the first line.
    findings.sort(key=lambda f: (f.file, f.line, f.rule))
    seen = set()
    out = []
    for f in findings:
        key = (f.file, f.rule, f.claimed, f.conflict)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


# ---------------------------------------------------------------------------
# Per-file rules R1-R6 (each takes a place claim + its paired signals)


def check_phone_vs_country(fpath, name, iso2, anchor, scope, findings):
    for s in scope:
        if s.category != "phone":
            continue
        countries = s.value.split("|")[-1].split(",") if "|" in s.value else []
        if countries and iso2 not in countries:
            findings.append(Finding(
                fpath, anchor, "R1", "inferred",
                '"%s" (place, explicit)' % name,
                'phone %s -> %s (inferred, via country calling code)'
                % (s.raw, ",".join(countries)),
                "error"))


def check_tz_vs_place(fpath, name, iso2, anchor, scope, findings):
    for s in scope:
        if s.category != "timezone":
            continue
        off = _tz_offset(s)
        if off is None:
            continue
        if not _offsets_consistent(iso2, off):
            info = COUNTRIES.get(iso2)
            band = ",".join(_fmt_offset(o) for o in (info.tz_offsets if info else []))
            findings.append(Finding(
                fpath, anchor, "R2", "inferred",
                '"%s" (place, explicit)' % name,
                'timezone %s not in %s tz band [%s] (inferred, via UTC offset table)'
                % (s.raw, iso2, band),
                "error"))


def check_currency_vs_country(fpath, name, iso2, anchor, scope, findings):
    for s in scope:
        if s.category != "currency":
            continue
        codes = _currency_codes(s)
        if not _currency_consistent(iso2, codes):
            info = COUNTRIES.get(iso2)
            legal = ",".join(info.currencies if info else [])
            findings.append(Finding(
                fpath, anchor, "R3", "inferred",
                '"%s" (place, explicit)' % name,
                'currency %s -> %s not legal tender in %s (%s) '
                '(inferred, via ISO 4217)' % (s.raw, "/".join(sorted(codes)),
                                              iso2, legal),
                "error"))


def check_coord_vs_country(fpath, name, iso2, anchor, scope, findings):
    for s in scope:
        if s.category != "coord":
            continue
        try:
            lat, lon = (float(x) for x in s.value.split(","))
        except ValueError:
            continue
        if not _in_bbox(iso2, lat, lon):
            findings.append(Finding(
                fpath, anchor, "R4", "inferred",
                '"%s" (place, explicit)' % name,
                'coord %s outside approximate bbox of %s (inferred, via '
                'country bounding box; coarse-grained, not precise reverse '
                'geocoding)' % (s.raw, iso2),
                "error"))


def check_locale_file_level(fpath, place_countries, signals, findings):
    """R5: every resolvable locale region must be among claimed countries."""
    if not place_countries:
        return
    for s in signals:
        if s.category != "locale":
            continue
        parts = s.value.split("-")
        region = parts[-1].upper() if len(parts) > 1 else None
        if region is None or region not in COUNTRIES:
            continue  # language-only tag or unknown region: never flag
        if region not in place_countries:
            findings.append(Finding(
                fpath, s.line, "R5", "inferred",
                '"%s" (locale, explicit)' % s.raw,
                'locale %s -> region %s not among claimed countries {%s} '
                '(inferred, via BCP47 region subtag)'
                % (s.value, region, ",".join(sorted(place_countries))),
                "error"))


def check_map_vs_place(fpath, name, iso2, anchor, scope, findings):
    for s in scope:
        if s.category != "map":
            continue
        kind, _, payload = s.value.partition(":")
        if kind == "place":
            target = _PLACE_INDEX.get(payload.strip().lower())
            if target is None:
                continue  # unresolvable place: never flag
            if target != iso2:
                findings.append(Finding(
                    fpath, anchor, "R6", "inferred",
                    '"%s" (place, explicit)' % name,
                    'map embed targets %s (%s) but content claims %s '
                    '(inferred, via map URL parameter)' % (payload, target, iso2),
                    "error"))
            elif payload.strip().lower() != name.lower():
                findings.append(Finding(
                    fpath, anchor, "R6", "inferred",
                    '"%s" (place, explicit)' % name,
                    'map embed targets %s but content claims %s '
                    '(warning: same country %s, different city)'
                    % (payload, name, iso2),
                    "warning"))
        elif kind == "coord":
            try:
                lat, lon = (float(x) for x in payload.split(","))
            except ValueError:
                continue
            if not _in_bbox(iso2, lat, lon):
                findings.append(Finding(
                    fpath, anchor, "R6", "inferred",
                    '"%s" (place, explicit)' % name,
                    'map embed coord %s outside approximate bbox of %s '
                    '(inferred, via map URL; coarse bbox, not precise '
                    'reverse geocoding)' % (payload, iso2),
                    "error"))


def _corroborated_anywhere(iso2, all_signals):
    """True if any signal anywhere in scope is consistent with iso2 (R7)."""
    info = COUNTRIES.get(iso2)
    for s in all_signals:
        if s.category == "phone" and "|" in s.value:
            if iso2 in s.value.split("|")[-1].split(","):
                return True
        elif s.category == "currency":
            if _currency_consistent(iso2, _currency_codes(s)):
                return True
        elif s.category == "timezone":
            # Only IANA zone names corroborate (zone -> home country is
            # precise). Raw UTC offsets are shared by many countries and
            # would produce false corroboration (e.g. UTC+1 covering both
            # Berlin and Zurich), so offsets never corroborate.
            if _tz_country(s) == iso2:
                return True
        elif s.category == "coord":
            try:
                lat, lon = (float(x) for x in s.value.split(","))
            except ValueError:
                continue
            if _in_bbox(iso2, lat, lon):
                return True
        elif s.category == "locale":
            parts = s.value.split("-")
            if len(parts) > 1 and parts[-1].upper() == iso2:
                return True
        elif s.category == "map":
            kind, _, payload = s.value.partition(":")
            if kind == "place":
                if _PLACE_INDEX.get(payload.strip().lower()) == iso2:
                    return True
            elif kind == "coord":
                try:
                    lat, lon = (float(x) for x in payload.split(","))
                except ValueError:
                    continue
                if _in_bbox(iso2, lat, lon):
                    return True
    return False


def check_unverified(fpath, claims, all_signals, findings):
    """R7: place claims with no paired geo signal at all (then no consistent
    signal anywhere in scope). Claims already involved in R1-R6 contradictions
    have paired signals and are reported by those rules instead."""
    for (name, iso2), claim in sorted(claims.items()):
        if claim["signals"]:
            continue  # has related signals (consistent or not)
        if _corroborated_anywhere(iso2, all_signals):
            continue
        findings.append(Finding(
            fpath, min(claim["lines"]), "R7", "unverified",
            '"%s" (place, explicit)' % name,
            "no corroborating geo signal in scope (unverified)",
            "info"))


# ---------------------------------------------------------------------------
# Entry point


def run_checks(files_signals, active_rules, dir_mode=False):
    """Run active rules over per-file signals.

    files_signals: dict[str, list[Signal]] (file path -> extracted signals)
    active_rules: set of rule ids to run, e.g. {"R1", "R7"}
    dir_mode: True when scanning a directory (corroboration scope = whole
              directory); False for single-file input.
    Returns findings sorted by (file, line, rule).
    """
    findings = []
    all_signals = [s for sigs in files_signals.values() for s in sigs]

    for fpath, signals in sorted(files_signals.items()):
        claims = _pair_signals(signals)
        place_countries = {key[1] for key in claims}

        if "R5" in active_rules:
            check_locale_file_level(fpath, place_countries, signals, findings)

        for (name, iso2), claim in sorted(claims.items()):
            anchor = min(claim["lines"])
            scope = claim["signals"]
            if "R1" in active_rules:
                check_phone_vs_country(fpath, name, iso2, anchor, scope, findings)
            if "R2" in active_rules:
                check_tz_vs_place(fpath, name, iso2, anchor, scope, findings)
            if "R3" in active_rules:
                check_currency_vs_country(fpath, name, iso2, anchor, scope, findings)
            if "R4" in active_rules:
                check_coord_vs_country(fpath, name, iso2, anchor, scope, findings)
            if "R6" in active_rules:
                check_map_vs_place(fpath, name, iso2, anchor, scope, findings)

        if "R7" in active_rules:
            scope_pool = all_signals if dir_mode else signals
            check_unverified(fpath, claims, scope_pool, findings)

    findings = _dedupe(findings)
    findings.sort(key=lambda f: (f.file, f.line, f.rule))
    return findings
