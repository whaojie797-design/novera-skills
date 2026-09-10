# -*- coding: utf-8 -*-
"""extract.py - Signal extraction for geo-evidence-audit.

Extracts 7 signal categories from text with line/column locations:
  phone, coord, place, currency, timezone, locale, map

All extraction is offline regex + built-in word lists (geo_data). No logic
beyond matching/normalization lives here; cross-signal checks are in rules.py.

Dependency direction: extract -> geo_data (never the reverse).
"""

import re
from dataclasses import dataclass

from geo_data import (
    COUNTRIES,
    COUNTRY_ALIASES,
    CURRENCY_SYMBOLS,
    IANA_TZ_OFFSETS,
)

SUPPORTED_EXTENSIONS = {
    ".md", ".markdown", ".txt", ".html", ".htm",
    ".json", ".csv", ".xml", ".yaml", ".yml",
}


@dataclass
class Signal:
    category: str   # phone|coord|place|currency|timezone|locale|map
    value: str      # normalized payload
    line: int       # 1-based line number
    col: int        # 1-based column of match start
    strength: str   # explicit for directly-written signals
    raw: str        # raw matched text


# ---------------------------------------------------------------------------
# Phone: E.164 style with common typography, e.g. +86 21 6333 5288,
# +1 (212) 555-0100, +49-30-555-0143. Requires a leading "+".
_PHONE_RE = re.compile(r"\+\d{1,3}[\s\-()]*(?:\d[\s\-()]*){6,14}")


def _phone_country(digits: str):
    """Map the digits after '+' to a set of ISO2 codes via calling codes."""
    for width in (3, 2, 1):
        if len(digits) >= width:
            code = digits[:width]
            hits = set()
            for iso2, info in COUNTRIES.items():
                if code in info.calling_codes:
                    hits.add(iso2)
            if hits:
                return hits
    return None


def _normalize_phone(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip()


# ---------------------------------------------------------------------------
# Coord: decimal pair "31.2304, 121.4737" and degree format "31.23°N, 121.47°E".
_DECIMAL_COORD_RE = re.compile(
    r"(?<![\w.\-])(-?\d{1,2}\.\d{1,6})\s*,\s*(-?\d{1,3}\.\d{1,6})(?![\w.\-])"
)
_DEG_COORD_RE = re.compile(
    r"(\d{1,2}(?:\.\d+)?)\s*°\s*([NSns])\s*[,，]\s*(\d{1,3}(?:\.\d+)?)\s*°\s*([EWew])"
)


def _valid_lat(lat: float) -> bool:
    return -90.0 <= lat <= 90.0


def _valid_lon(lon: float) -> bool:
    return -180.0 <= lon <= 180.0


# ---------------------------------------------------------------------------
# Place: built from country data at import time (word lists, not logic).
def _build_place_index():
    index = {}
    for iso2, info in COUNTRIES.items():
        names = set(info.cities_en)
        names.add(info.name_en)
        for name in names:
            index.setdefault(name.lower(), iso2)
    for alias, iso2 in COUNTRY_ALIASES.items():
        index.setdefault(alias.lower(), iso2)
    return index


_PLACE_INDEX = _build_place_index()
_PLACE_ZH = {}
for _iso2, _info in COUNTRIES.items():
    for _name in list(_info.cities_zh) + [_info.name_zh]:
        _PLACE_ZH.setdefault(_name, _iso2)

_PLACE_ZH_ORDER = sorted(_PLACE_ZH, key=len, reverse=True)

_ASCII_PLACE_RE = re.compile(
    r"\b(" + "|".join(
        re.escape(n) for n in sorted(_PLACE_INDEX, key=len, reverse=True)
    ) + r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Currency: symbols plus ISO 4217 codes present in the country data.
_CURRENCY_CODE_RE = re.compile(
    r"\b(" + "|".join(sorted(
        {c for info in COUNTRIES.values() for c in info.currencies}
        | {c for codes in CURRENCY_SYMBOLS.values() for c in codes},
        key=len, reverse=True)) + r")\b"
)
_CURRENCY_SYMBOL_RE = re.compile(
    "[" + re.escape("".join(CURRENCY_SYMBOLS.keys())) + "]"
)


# ---------------------------------------------------------------------------
# Timezone: IANA zone names and UTC/GMT offsets.
_IANA_TZ_RE = re.compile(
    r"\b(Africa|America|Antarctica|Asia|Atlantic|Australia|Europe|Indian|Pacific)"
    r"/[A-Za-z][A-Za-z_]*(?:/[A-Za-z][A-Za-z_]*)?\b"
)
_TZ_OFFSET_RE = re.compile(r"\b(?:UTC|GMT)\s*([+\-])\s*(\d{1,2})(?::(\d{2}))?\b")


def _offset_from_iana(name: str):
    off = IANA_TZ_OFFSETS.get(name)
    if off is None:
        return None
    return off


# ---------------------------------------------------------------------------
# Locale: lang/hreflang attributes and xml:lang.
_LOCALE_RE = re.compile(
    r"\b(?:hreflang|xml:lang|lang)\s*[:=]\s*[\"']?"
    r"([a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*)[\"']?"
)


# ---------------------------------------------------------------------------
# Map embeds: Google Maps / OSM / Bing Maps URLs and iframe src.
_MAP_URL_RE = re.compile(
    r"\bhttps?://[^\s\"'<>]*(?:google\.[a-z.]+/maps|"
    r"(?:www\.)?(?:openstreetmap\.org|osm\.org)|bing\.com/maps)"
    r"[^\s\"'<>]*",
    re.IGNORECASE,
)
_MAP_AT_COORD_RE = re.compile(r"@(-?\d{1,2}\.\d+),(-?\d{1,3}\.\d+)")
_MAP_HASH_COORD_RE = re.compile(r"#map=\d+(?:/\d+)?/(-?\d{1,2}\.\d+)/(-?\d{1,3}\.\d+)")
_MAP_Q_RE = re.compile(r"[?&]q=([^&\s\"']+)")
_MAP_Q_COORD_RE = re.compile(r"^-?\d{1,2}\.\d+\s*,\s*-?\d{1,3}\.\d+$")


def _parse_map_url(url: str):
    """Return ('place', name) or ('coord', 'lat,lon') or None."""
    m = _MAP_Q_RE.search(url)
    if m:
        val = m.group(1)
        if _MAP_Q_COORD_RE.match(val):
            return ("coord", val)
        from urllib.parse import unquote
        return ("place", unquote(val))
    m = _MAP_AT_COORD_RE.search(url)
    if m:
        return ("coord", m.group(1) + "," + m.group(2))
    m = _MAP_HASH_COORD_RE.search(url)
    if m:
        return ("coord", m.group(1) + "," + m.group(2))
    return None


def extract_signals(text: str) -> list:
    """Extract all 7 signal categories; returns list[Signal] sorted by line."""
    signals = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        low = line

        # Map URLs first: place/coord matches INSIDE a map URL are part of
        # the map signal (handled by R6), not standalone textual claims.
        map_matches = list(_MAP_URL_RE.finditer(line))

        def _in_map(pos):
            return any(m.start() <= pos < m.end() for m in map_matches)

        for m in _PHONE_RE.finditer(line):
            digits = re.sub(r"\D", "", m.group(0))
            country = _phone_country(digits)
            signals.append(Signal(
                "phone", "+" + digits, lineno, m.start() + 1, "explicit",
                _normalize_phone(m.group(0)), ))
            if country:
                # keep resolved countries in value for rules: "+digits|US,CA"
                signals[-1].value = "+" + digits + "|" + ",".join(sorted(country))

        for m in _DECIMAL_COORD_RE.finditer(line):
            if _in_map(m.start()):
                continue
            lat, lon = float(m.group(1)), float(m.group(2))
            if _valid_lat(lat) and _valid_lon(lon):
                signals.append(Signal(
                    "coord", "%.4f,%.4f" % (lat, lon), lineno,
                    m.start() + 1, "explicit", m.group(0)))

        for m in _DEG_COORD_RE.finditer(line):
            if _in_map(m.start()):
                continue
            lat = float(m.group(1)) * (-1.0 if m.group(2).upper() == "S" else 1.0)
            lon = float(m.group(3)) * (-1.0 if m.group(4).upper() == "W" else 1.0)
            if _valid_lat(lat) and _valid_lon(lon):
                signals.append(Signal(
                    "coord", "%.4f,%.4f" % (lat, lon), lineno,
                    m.start() + 1, "explicit", m.group(0)))

        for m in _ASCII_PLACE_RE.finditer(line):
            if _in_map(m.start()):
                continue
            name = m.group(1)
            signals.append(Signal(
                "place", name + "|" + _PLACE_INDEX[name.lower()], lineno,
                m.start() + 1, "explicit", m.group(0)))

        for zh_name in _PLACE_ZH_ORDER:
            start = 0
            while True:
                idx = low.find(zh_name, start)
                if idx < 0:
                    break
                signals.append(Signal(
                    "place", zh_name + "|" + _PLACE_ZH[zh_name], lineno,
                    idx + 1, "explicit", zh_name))
                start = idx + len(zh_name)

        for m in _CURRENCY_CODE_RE.finditer(line):
            signals.append(Signal(
                "currency", m.group(1), lineno, m.start() + 1, "explicit",
                m.group(0)))
        for m in _CURRENCY_SYMBOL_RE.finditer(line):
            signals.append(Signal(
                "currency", m.group(0), lineno, m.start() + 1, "explicit",
                m.group(0)))

        for m in _IANA_TZ_RE.finditer(line):
            off = _offset_from_iana(m.group(0))
            value = m.group(0) + ("|%.2f" % off if off is not None else "")
            signals.append(Signal(
                "timezone", value, lineno, m.start() + 1, "explicit",
                m.group(0)))
        for m in _TZ_OFFSET_RE.finditer(line):
            sign = -1.0 if m.group(1) == "-" else 1.0
            minutes = float(m.group(3)) / 60.0 if m.group(3) else 0.0
            off = sign * (float(m.group(2)) + minutes)
            signals.append(Signal(
                "timezone", "UTC%+.2f" % off, lineno, m.start() + 1,
                "explicit", m.group(0)))

        for m in _LOCALE_RE.finditer(line):
            signals.append(Signal(
                "locale", m.group(1), lineno, m.start() + 1, "explicit",
                m.group(0)))

        for m in _MAP_URL_RE.finditer(line):
            parsed = _parse_map_url(m.group(0))
            if parsed:
                signals.append(Signal(
                    "map", parsed[0] + ":" + parsed[1], lineno,
                    m.start() + 1, "explicit", m.group(0)))
            else:
                signals.append(Signal(
                    "map", "url:", lineno, m.start() + 1, "explicit",
                    m.group(0)))

    # Deduplicate identical (category, value, line) entries, keep order.
    seen = set()
    unique = []
    for s in signals:
        key = (s.category, s.value, s.line, s.col)
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique
