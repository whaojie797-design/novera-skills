# -*- coding: utf-8 -*-
"""checkers.py - V1-V10 rule implementations + inventory assembly.

Groups (design 3.2):
- completeness V1-V2, consistency V3-V5, image-spec V6-V9 (verified
  platform snapshots only by default), compliance hint V10.
- inventory: image placements + spec declarations, informational, never
  affects the exit code (design A12 / supply-chain refs precedent).

All literal/lexicon level; no semantics, no image reading, no network.
Dependency direction: checkers -> {brief_data, platform_specs, briefparse}.
"""

import re

import briefparse
from brief_data import (
    CATEGORY_DECLS,
    CATEGORY_SCENE_CONFLICTS,
    COMPARATIVE_SAFE_MARKERS,
    CURRENCY_LOCALE,
    DISCLAIMER,
    EXTREME_WORDS,
    REQUIRED_FIELDS,
)
from platform_specs import PLATFORMS

_CURRENCY_RE = re.compile(r"[$¥€£]|(?:CNY|RMB|USD|JPY|EUR|GBP)\b", re.I)
_LOCALE_VAL_RE = re.compile(r"([a-z]{2}-[a-zA-Z]{2})")   # zh-cn / zh-CN
_CLAIM_EVIDENCE_RE = re.compile(r"(?:附|见|配|参见)\s*(?:图\s*\d+|\S*图\S*)")


def _finding(file, line, rule, strength, field_name, value, expected):
    from report import Finding
    return Finding(file=file, line=line, rule=rule, strength=strength,
                   field=field_name, value=value, expected=expected)


def _convention_note(what):
    return ("%s is a default convention (see references/rules.md), "
            "not a fact" % what)


def run_validate(briefs, spec=None, include_unverified=False):
    """V1-V10 over parsed briefs. spec=None => V6-V9 skipped (note)."""
    findings = []
    for brief in briefs:
        findings.extend(_v1_required(brief))
        findings.extend(_v2_category_decls(brief))
        findings.extend(_v3_currency(brief))
        findings.extend(_v4_claim_evidence(brief))
        findings.extend(_v5_category_scene(brief))
        if spec is not None:
            findings.extend(_v6_v9_image_specs(brief, spec,
                                               include_unverified))
        findings.extend(_v10_extreme_words(brief))
    findings.sort(key=lambda f: (f.file, f.line, f.rule))
    return findings


# ---------------------------------------------------------------------------
# V1 missing-required-field
# ---------------------------------------------------------------------------

def _v1_required(brief):
    out = []
    for field_name in REQUIRED_FIELDS:
        if field_name not in brief.fields:
            out.append(_finding(
                brief.path, 1, "V1", "explicit", field_name, "(missing)",
                "required field per novera brief baseline (%s)"
                % _convention_note("required set")))
    return out


# ---------------------------------------------------------------------------
# V2 missing-category-declaration
# ---------------------------------------------------------------------------

def _v2_category_decls(brief):
    out = []
    category = None
    for key in ("category", "品类", "product_category"):
        if key in brief.fields:
            category = brief.fields[key].value
            break
    if not category:
        return out
    for cat_key, decls in CATEGORY_DECLS.items():
        if cat_key not in category:
            continue
        whole_text = _whole_text(brief)
        for decl in decls:
            if decl not in whole_text:
                out.append(_finding(
                    brief.path,
                    brief.fields.get("category",
                                     brief.fields.get("品类",
                                                      brief.fields.get(
                                                          "product_category"))
                                     ).line if any(
                        k in brief.fields for k in
                        ("category", "品类", "product_category")) else 1,
                    "V2", "inferred",
                    "category=%s" % category,
                    "declaration keyword \"%s\" absent" % decl,
                    "category-required declaration (%s)" % _convention_note(
                        "category mapping")))
                break   # one finding per category hit
        break
    return out


def _whole_text(brief):
    # keys included: a declaration may be carried by the key itself
    # (e.g. a "成分: 玻尿酸" line declares the 成分 keyword)
    parts = ["%s: %s" % (key, fv.value)
             for key, fv in brief.fields.items()]
    parts.extend(c.text for c in brief.claims)
    parts.extend(p.text for p in brief.placements)
    parts.extend(s.raw for s in brief.image_specs)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# V3 pricing-locale-mismatch
# ---------------------------------------------------------------------------

def _v3_currency(brief):
    price_val = None
    price_line = 1
    locale_val = None
    locale_line = 1
    for key, fv in brief.fields.items():
        if price_val is None and briefparse.is_price_key(key):
            price_val, price_line = fv.value, fv.line
        if locale_val is None and briefparse.is_locale_key(key):
            locale_val, locale_line = fv.value, fv.line
    if not price_val or not locale_val:
        return []
    m = _LOCALE_VAL_RE.search(locale_val)
    if not m:
        return []
    locale = m.group(1).lower()
    allowed = CURRENCY_LOCALE.get(locale)
    if allowed is None:
        return []          # unknown locale: not decidable, stay silent
    found = _CURRENCY_RE.findall(price_val)
    for token in found:
        token_l = token.lower()
        if token_l in allowed:
            continue
        if token == "¥" and locale in CURRENCY_LOCALE and \
                any(t in allowed for t in ("¥", "cny", "rmb")):
            continue
        return [_finding(
            brief.path, price_line, "V3", "inferred",
            "pricing / locale",
            'price "%s" uses "%s" while locale declares "%s"'
            % (price_val, token, locale),
            "currency consistent with locale (%s)" % _convention_note(
                "currency-locale table"))]
    return []


# ---------------------------------------------------------------------------
# V4 claim-evidence-gap
# ---------------------------------------------------------------------------

def _v4_claim_evidence(brief):
    out = []
    if not brief.placements:
        placement_labels = set()
    else:
        placement_labels = {p.label.replace(" ", "") for p in brief.placements}
    for claim in brief.claims:
        m = re.search(r"图\s*(\d+)", claim.text)
        if not m:
            continue          # claim does not reference an image: OK
        label = "图%s" % m.group(1)
        if label not in placement_labels:
            out.append(_finding(
                brief.path, claim.line, "V4", "inferred",
                "claim[%d]" % claim.index,
                '"%s" references %s' % (claim.text[:60], label),
                "referenced placement present in inventory (placements: %s)"
                % (", ".join(sorted(placement_labels)) or "none")))
    return out


# ---------------------------------------------------------------------------
# V5 category-scene-mismatch
# ---------------------------------------------------------------------------

def _v5_category_scene(brief):
    out = []
    category = None
    for key in ("category", "品类", "product_category"):
        if key in brief.fields:
            category = brief.fields[key].value
            break
    if not category:
        return []
    scene_val = None
    scene_line = 1
    for key in ("scene", "场景", "拍摄场景", "scene_setting"):
        if key in brief.fields:
            scene_val = brief.fields[key].value
            scene_line = brief.fields[key].line
            break
    if not scene_val:
        for claim in brief.claims:
            if re.search(r"场景|模特", claim.text):
                scene_val, scene_line = claim.text, claim.line
                break
    if not scene_val:
        return []
    for cat_key, conflicts in CATEGORY_SCENE_CONFLICTS.items():
        if cat_key not in category:
            continue
        for word in sorted(conflicts):
            if word in scene_val:
                out.append(_finding(
                    brief.path, scene_line, "V5", "inferred",
                    "category / scene",
                    'category "%s" conflicts with scene word "%s"'
                    % (category, word),
                    "category-scene conflict pair (%s)" % _convention_note(
                        "conflict mapping")))
                break
    return out


# ---------------------------------------------------------------------------
# V6-V9 image specs against a platform snapshot
# ---------------------------------------------------------------------------

def _v6_v9_image_specs(brief, spec, include_unverified):
    out = []
    for s in brief.image_specs:
        target = spec
        if s.platform_hint and s.platform_hint in PLATFORMS and \
                s.platform_hint != spec.slug:
            continue          # declaration targets another platform
        if not spec.verified and not include_unverified:
            continue          # unverified platform: default skip (A5)
        if not spec.verified and include_unverified:
            if _has_checkable_data(s):
                out.append(_finding(
                    brief.path, s.line, "V6", "unverified",
                    "image spec",
                    'platform "%s" snapshot is unverified; spec not '
                    "checkable" % spec.slug,
                    "verified platform snapshot or drop the platform tag"))
            continue
        # verified (or explicitly included) platform:
        if spec.verified and not _has_checkable_data(s) and \
                not _has_checkable_data(spec):
            continue
        if s.fmt and spec.formats and s.fmt not in spec.formats:
            out.append(_finding(
                brief.path, s.line, "V6", "explicit", "image format",
                'declared format "%s"' % s.fmt,
                "one of %s per verified snapshot %s (%s)"
                % (",".join(spec.formats), spec.slug, spec.source_url)))
        if (s.width or s.height) and (spec.min_long_side is not None or
                                      spec.max_long_side is not None):
            for side in (s.width, s.height):
                if side is None:
                    continue
                if spec.min_long_side is not None and \
                        side < spec.min_long_side:
                    out.append(_finding(
                        brief.path, s.line, "V7", "explicit",
                        "image dimension",
                        "declared %dx%d (%d px below minimum %d)"
                        % (s.width, s.height, side, spec.min_long_side),
                        "longest side >= %d per verified snapshot %s (%s)"
                        % (spec.min_long_side, spec.slug, spec.source_url)))
                    break
                if spec.max_long_side is not None and \
                        side > spec.max_long_side:
                    out.append(_finding(
                        brief.path, s.line, "V7", "explicit",
                        "image dimension",
                        "declared %dx%d (%d px above maximum %d)"
                        % (s.width, s.height, side, spec.max_long_side),
                        "longest side <= %d per verified snapshot %s (%s)"
                        % (spec.max_long_side, spec.slug, spec.source_url)))
                    break
        if s.count is not None and spec.main_image_count:
            lo, hi = spec.main_image_count
            if (lo is not None and s.count < lo) or \
                    (hi is not None and s.count > hi):
                bound = (">= %d" % lo) if (hi is None and lo is not None) \
                    else ("<= %d" % hi if lo is None else "%d-%d" % (lo, hi))
                out.append(_finding(
                    brief.path, s.line, "V8", "explicit",
                    "main image count",
                    "declared %d main image(s), snapshot allows %s"
                    % (s.count, bound),
                    "main image count %s per verified snapshot %s (%s)"
                    % (bound, spec.slug, spec.source_url)))
        if s.white_bg is False and spec.whitespace_required:
            out.append(_finding(
                brief.path, s.line, "V9", "explicit", "image background",
                'declaration "%s" (non-white background)' % s.raw[:60],
                "white background required per verified snapshot %s (%s)"
                % (spec.slug, spec.source_url)))
    return out


def _has_checkable_data(obj):
    if isinstance(obj, briefparse.ImageSpec):
        return bool(obj.fmt or obj.width or obj.height or obj.count is not None
                    or obj.white_bg is not None)
    return bool(obj.formats or obj.min_long_side is not None
                or obj.max_long_side is not None
                or obj.main_image_count or obj.whitespace_required is not None)


# ---------------------------------------------------------------------------
# V10 extreme-word risk (lexicon hint, never legal)
# ---------------------------------------------------------------------------

def _v10_extreme_words(brief):
    out = []
    lines = _iter_content_lines(brief)
    for line_no, text in lines:
        low = text.lower()
        if any(marker in low or marker in text
               for marker in COMPARATIVE_SAFE_MARKERS):
            continue
        for wp in EXTREME_WORDS:
            if re.search(wp.regex, text, re.I):
                out.append(_finding(
                    brief.path, line_no, "V10", "explicit",
                    "lexicon hit: %s" % wp.label,
                    '"%s"' % text.strip()[:70],
                    "extreme-word risk hint (%s)" % DISCLAIMER))
                break          # one hit per line
    return out


def _iter_content_lines(brief):
    for key, fv in sorted(brief.fields.items()):
        if fv.value:
            yield fv.line, fv.value
    for c in brief.claims:
        yield c.line, c.text
    for p in brief.placements:
        yield p.line, p.text
    for s in brief.image_specs:
        yield s.line, s.raw


# ---------------------------------------------------------------------------
# inventory (informational, never affects exit code)
# ---------------------------------------------------------------------------

def run_inventory(briefs):
    from report import Inventory
    items = []
    for brief in briefs:
        for p in brief.placements:
            items.append(("placement", brief.path, p.line,
                          p.text[:60]))
        for s in brief.image_specs:
            items.append(("image-spec", brief.path, s.line,
                          s.raw[:80] + (" [%s]" % s.platform_hint
                                        if s.platform_hint else "")))
    items.sort(key=lambda t: (t[2], t[1], t[0]))
    return Inventory(items=items)
