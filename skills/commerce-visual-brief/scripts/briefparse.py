# -*- coding: utf-8 -*-
"""briefparse.py - offline brief document parsing (listing.py pattern reuse).

Parses md/markdown/txt (frontmatter + key:value lines + H2 sections),
json (flat top-level dict, per-key line numbers), yaml subset (flat
key:value lines) and csv (header + rows). Everything carries a line number
so findings can point at file:line (family convention).

Detection is literal/lexicon level only (design A7): no semantics, no
image reading, no network. Returns None when the text carries no brief
structure at all (CLI turns that into exit 2).

Dependency direction: briefparse -> (nothing from this skill).
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FieldValue:
    value: str
    line: int


@dataclass
class Claim:
    index: int
    text: str
    line: int


@dataclass
class Placement:
    label: str          # e.g. "图3" / "图 3"
    text: str
    line: int


@dataclass
class ImageSpec:
    line: int
    raw: str
    platform_hint: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fmt: Optional[str] = None
    count: Optional[int] = None
    white_bg: Optional[bool] = None   # True=declared white, False=declared
                                      # non-white, None=silent


@dataclass
class Brief:
    path: str
    fmt: str                    # md | txt | json | yaml | csv
    fields: dict = field(default_factory=dict)
    claims: list = field(default_factory=list)
    placements: list = field(default_factory=list)
    image_specs: list = field(default_factory=list)

    def has_structure(self):
        return bool(self.fields or self.claims or self.placements
                    or self.image_specs)


BRIEF_EXTENSIONS = (".md", ".markdown", ".txt", ".html", ".htm",
                    ".json", ".yaml", ".yml", ".csv")

_DIM_RE = re.compile(r"(\d{2,5})\s*[xX×*]\s*(\d{2,5})")
_COUNT_RE = re.compile(r"(\d+)\s*张")
_WHITE_RE = re.compile(r"(?:纯白|白底|白色背景|白背景|white\s+background)",
                       re.I)
_NONWHITE_BG_RE = re.compile(
    r"(?:浅灰|灰色|黑色|彩色|渐变|场景图|非白底|灰色背景|黑底)", re.I)
_FMT_RE = re.compile(
    r"\b(jpg|jpeg|png|gif|webp|tiff?|bmp|heic)\b", re.I)
_PLACEMENT_RE = re.compile(r"图\s*(\d+)\s*[:：]")
_PLATFORM_HINTS = (
    ("taobao", ("taobao", "淘宝")),
    ("tmall", ("tmall", "天猫")),
    ("jd", ("jd", "京东")),
    ("pdd", ("pdd", "pinduoduo", "拼多多")),
    ("amazon", ("amazon", "亚马逊")),
)
_CLAIM_KEY_RE = re.compile(r"^(?:卖点|selling[_\s-]?points?|claims?)$")
_LOCALE_KEY_RE = re.compile(r"^(?:locale|语言|lang(?:uage)?)$")
_PRICE_KEY_RE = re.compile(r"^(?:pricing|price|价格|售价|定价)$")


def _norm_key(key):
    return re.sub(r"[\s\-]+", "_", key.strip().lower())


def _platform_hint(text):
    low = text.lower()
    for slug, markers in _PLATFORM_HINTS:
        for m in markers:
            if m in low or m in text:
                return slug
    return None


def _scan_line_for_spec(line_no, raw):
    """Literal extraction of an image-spec declaration from one line."""
    text = raw.strip()
    if not text:
        return None
    dim = _DIM_RE.search(text)
    count = _COUNT_RE.search(text)
    fmt = _FMT_RE.search(text)
    white = None
    # non-white markers first: "非白底" contains the substring "白底",
    # so the white test must run second (design 3.2: literal, but sane)
    if _NONWHITE_BG_RE.search(text):
        white = False
    elif _WHITE_RE.search(text):
        white = True
    if dim is None and count is None and fmt is None and white is None:
        return None
    hint = _platform_hint(text)
    return ImageSpec(
        line=line_no, raw=text[:120],
        platform_hint=hint,
        width=int(dim.group(1)) if dim else None,
        height=int(dim.group(2)) if dim else None,
        fmt=fmt.group(1).lower() if fmt else None,
        count=int(count.group(1)) if count else None,
        white_bg=white,
    )


def _spec_relevant(raw):
    """A spec declaration must sit on a line that mentions images/photos,
    so random numbers elsewhere are not misread (design 3.2)."""
    return bool(re.search(r"主图|图片|图位|规格|照片|image|photo|img",
                          raw, re.I))


def parse_brief(text, path):
    """Parse one brief file; returns Brief or None (no brief structure)."""
    ext = path.lower().rsplit(".", 1)[-1]
    if ext == "json":
        brief = _parse_json(text, path)
    elif ext in ("yaml", "yml"):
        brief = _parse_yaml(text, path)
    elif ext == "csv":
        brief = _parse_csv(text, path)
    elif ext in ("html", "htm"):
        brief = _parse_kv_lines(_strip_html(text), path, "html")
    else:
        brief = _parse_kv_lines(text, path, ext or "txt")
    if brief is None or not brief.has_structure():
        return None
    return brief


def _add_field(brief, key, value, line):
    k = _norm_key(key)
    if k and k not in brief.fields:
        brief.fields[k] = FieldValue(value=str(value).strip(), line=line)


def _add_claim(brief, text, line):
    text = text.strip()
    if text:
        brief.claims.append(Claim(index=len(brief.claims), text=text,
                                  line=line))


def _add_placement(brief, text, line):
    m = _PLACEMENT_RE.search(text)
    if m:
        label = "图%s" % m.group(1)
        if not any(p.label == label for p in brief.placements):
            brief.placements.append(Placement(label=label, text=text.strip(),
                                              line=line))


def _kv_line(line):
    """Split 'key: value' or 'key：value'; None if not a kv line."""
    m = re.match(r"^\s*[-*•]?\s*([A-Za-z_\u4e00-\u9fff][^:：]{0,40})[:：]"
                 r"\s*(.*)$", line)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


def _parse_kv_lines(text, path, fmt):
    brief = Brief(path=path, fmt=fmt)
    in_frontmatter = False
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        stripped = line.strip()
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if stripped.startswith("#"):            # headings: skip, keep specs
            spec = _scan_line_for_spec(line_no, stripped.lstrip("#").strip())
            if spec and _spec_relevant(stripped):
                brief.image_specs.append(spec)
            continue
        if _PLACEMENT_RE.search(stripped):
            _add_placement(brief, stripped, line_no)
        claim_hit = bool(re.search(r"卖点|selling[_\s-]?point", stripped, re.I))
        if claim_hit:
            value = re.sub(r"^[-*•]?\s*(?:卖点\d*\s*[:：]?)?\s*", "",
                           stripped, flags=re.I)
            _add_claim(brief, value, line_no)
        kv = _kv_line(line)
        if kv and not claim_hit:
            # a selling-point line is a claim, not a field: counting it in
            # both sources would double-report V10 hits on the same line
            key, value = kv
            _add_field(brief, key, value, line_no)
        spec = _scan_line_for_spec(line_no, stripped)
        if spec and _spec_relevant(stripped):
            brief.image_specs.append(spec)
    return brief


def _parse_json(text, path):
    try:
        doc = json.loads(text)
    except ValueError:
        return Brief(path=path, fmt="json")   # invalid JSON -> no structure
    if not isinstance(doc, dict):
        return Brief(path=path, fmt="json")
    brief = Brief(path=path, fmt="json")
    lines = text.splitlines()
    key_line = {}
    for line_no, raw in enumerate(lines, start=1):
        m = re.match(r'^\s*"([^"]+)"\s*:', raw)
        if m and m.group(1) not in key_line:
            key_line[m.group(1)] = line_no
    for key, value in doc.items():
        line_no = key_line.get(key, 1)
        if isinstance(value, (str, int, float)):
            _add_field(brief, key, value, line_no)
        elif key and _CLAIM_KEY_RE.match(_norm_key(key)) and \
                isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    _add_claim(brief, item, line_no)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    if _PLACEMENT_RE.search(item):
                        _add_placement(brief, item, line_no)
                    else:
                        _add_claim(brief, item, line_no)
        elif isinstance(value, dict):
            for k2, v2 in value.items():
                if isinstance(v2, (str, int, float)):
                    _add_field(brief, key + "_" + k2, v2, line_no)
    for line_no, raw in enumerate(lines, start=1):
        spec = _scan_line_for_spec(line_no, raw)
        if spec and _spec_relevant(raw):
            brief.image_specs.append(spec)
    return brief


def _parse_yaml(text, path):
    return _parse_kv_lines(text, path, "yaml")


def _parse_csv(text, path):
    brief = Brief(path=path, fmt="csv")
    rows = list(csv_rows(text))
    if not rows:
        return brief
    header = rows[0]
    for row in rows[1:]:
        for col, value in zip(header, row):
            if not col:
                continue
            _add_field(brief, col, value, 1)
    for line_no, raw in enumerate(text.splitlines(), start=1):
        spec = _scan_line_for_spec(line_no, raw)
        if spec and _spec_relevant(raw):
            brief.image_specs.append(spec)
        if _PLACEMENT_RE.search(raw):
            _add_placement(brief, raw, line_no)
    return brief


def csv_rows(text):
    """Minimal CSV split (flat rows, comma-separated, no quoting support
    beyond stripping) - keeps the module dependency-free and simple."""
    rows = []
    for line in text.splitlines():
        if line.strip():
            rows.append([cell.strip() for cell in line.split(",")])
    return rows


def _strip_html(text):
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", text)
    text = re.sub(r"(?s)<[^>]+>", "\n", text)
    return text


def is_price_key(key):
    return bool(_PRICE_KEY_RE.match(key))


def is_locale_key(key):
    return bool(_LOCALE_KEY_RE.match(key))
