# -*- coding: utf-8 -*-
"""brief_data.py - pure data module for commerce-visual-brief.

Contains: the required-field baseline, the extreme-word lexicon, the
category -> required-declaration mapping, the category -> scene conflict
pairs, and the currency/locale table.

Honesty marks (family convention):
- REQUIRED_FIELDS, CATEGORY_DECLS, CATEGORY_SCENE_CONFLICTS are drafting
  defaults, each marked default_convention: true. They are conventions,
  NOT verified facts; reports must label them as such.
- EXTREME_WORDS is a lexicon for RISK HINTS ONLY. A hit is never a legal
  determination (see DISCLAIMER).
Dependency direction: brief_data -> (nothing). Nobody may import back.
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# V1: required fields. default_convention: true (novera brief baseline).
# Category-specific compliance declarations are handled by V2 via
# CATEGORY_DECLS, NOT by this global set (avoids double reporting).
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = ("product_name", "pricing", "size_chart", "color_card")

# ---------------------------------------------------------------------------
# V10: extreme-word lexicon (Chinese-led, English support).
# Lexicon match = risk hint, NEVER a legal determination (design A6).
# ---------------------------------------------------------------------------
DISCLAIMER = ("lexicon hit is a risk hint, not a legal determination; "
              "check platform rules and applicable law")


@dataclass
class WordPattern:
    label: str
    regex: str


EXTREME_WORDS = (
    # "+" is mandatory: a bare "最" (e.g. "最近上新") has no extreme
    # semantics - the pattern requires an intensity word after it
    WordPattern("最X", r"最[高低好强大佳优快全新]+"),
    WordPattern("第一/No.1", r"(?:第一|No\.?1|#1|TOP\s*1)"),
    WordPattern("顶级/极品", r"(?:顶级|极品|极限|至尊)"),
    WordPattern("国家级", r"(?:国家级|世界级|全国级)"),
    WordPattern("全网最低/绝对", r"(?:全网最低|全网第一|绝对|百分百|100%)"),
    WordPattern("唯一/独家", r"(?:唯一|独家|首选|首个)"),
    WordPattern("治愈/根治类功效", r"(?:根治|治愈|包治|立竿见影)"),
    WordPattern("best/miracle (en)", r"\b(?:the\s+best|miracle|guaranteed\s+results)\b"),
)

# Comparative wording explicitly protected from V10 (design 3.2).
COMPARATIVE_SAFE_MARKERS = (
    "更耐用", "较上一代", "相比", "较之", "比上一代", "提升",
    "more durable", "compared to", "improved",
)

# ---------------------------------------------------------------------------
# V2: category -> required declaration keywords. default_convention: true.
# A brief whose category line hits a key below must contain each keyword
# somewhere in the brief, or V2 reports the first missing keyword.
# ---------------------------------------------------------------------------
CATEGORY_DECLS = {
    "化妆品": ("成分", "备案"),
    "护肤品": ("成分", "备案"),
    "食品": ("生产许可", "保质期"),
    "保健品": ("批准文号", "本品不能代替药物"),
    "母婴": ("材质安全", "认证"),
    "电器": ("3C", "保修"),
}

# ---------------------------------------------------------------------------
# V5: category -> scene conflict pairs. default_convention: true.
# Coarse literal mapping: if the brief names a category on the left and a
# scene keyword on the right, V5 reports the conflict pair. Scene words not
# present in any conflict pair are NOT reported (better to miss than to
# misreport, design 3.2).
# ---------------------------------------------------------------------------
CATEGORY_SCENE_CONFLICTS = {
    "母婴": frozenset({"酒吧", "夜店", "夜场", "酗酒", "赌"}),
    "医疗器械": frozenset({"酒吧", "夜店", "派对"}),
    "食品": frozenset({"有毒", "腐坏"}),
}

# ---------------------------------------------------------------------------
# V3: locale -> currency symbols/codes considered consistent.
# Literal table; a price in a symbol outside the locale's set while the
# brief declares that locale is reported. default_convention: true.
# ---------------------------------------------------------------------------
CURRENCY_LOCALE = {
    "zh-cn": frozenset({"¥", "cny", "rmb"}),
    "zh-cn/jp-note": frozenset(),
    "en-us": frozenset({"$", "usd"}),
    "en-gb": frozenset({"£", "gbp"}),
    "ja-jp": frozenset({"¥", "jpy", "円"}),
    "de-de": frozenset({"€", "eur"}),
    "fr-fr": frozenset({"€", "eur"}),
}

# Locales that legitimately use "¥" (CNY and JPY share the glyph).
CNY_JPY_SHARED = ("zh-cn", "ja-jp")
