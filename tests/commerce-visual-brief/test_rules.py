"""Rule-level behavior checks: V1-V10 signals, honesty labels, platform
flag semantics and counter-example protection for commerce-visual-brief."""

import json

import pytest

from tests.conftest import (
    CVB_FIXTURES as FIXTURES,
    cvb_run as run_cli,
    mini_dir,
)

RULE_IDS = {"V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10"}


def _rules(out):
    rules = set()
    for ln in out.splitlines():
        head = ln.split()
        if head and head[0] in RULE_IDS:
            rules.add(head[0])
    return rules


def _validate(name, *extra):
    return run_cli(["validate", str(FIXTURES / name)] + list(extra))


# --- V1 required fields ----------------------------------------------------

def test_v1_missing_pricing_anchors_line_one():
    code, out, err = _validate("missing-pricing.md")
    assert code == 1
    assert _rules(out) == {"V1"}, out
    assert "missing-pricing.md:1 [explicit] pricing" in out
    assert "(missing)" in out


def test_v1_missing_color_card_names_field():
    code, out, err = _validate("missing-color-card.md")
    assert code == 1
    assert _rules(out) == {"V1"}, out
    assert "color_card" in out


# --- V2 category declarations ----------------------------------------------

def test_v2_cosmetics_missing_declaration_is_convention_labelled():
    code, out, err = _validate("missing-compliance-decl.md")
    assert code == 1
    assert _rules(out) == {"V2"}, out
    assert "declaration keyword" in out
    # V2 maps via the category word table: must carry the convention label
    assert "default convention" in out


def test_v2_anchors_category_line():
    code, out, err = _validate("missing-compliance-decl.md")
    assert code == 1
    assert "missing-compliance-decl.md:7" in out   # category sits on line 7


def test_v2_known_category_not_flagged_when_decls_present():
    # category-scene-mismatch.md is 母婴 with 材质安全/认证 both present:
    # only V5 may fire there
    code, out, err = _validate("category-scene-mismatch.md")
    assert code == 1
    assert _rules(out) == {"V5"}, out


# --- V3 currency / locale ---------------------------------------------------

def test_v3_usd_against_zh_cn_locale():
    code, out, err = _validate("currency-mismatch.md")
    assert code == 1
    assert _rules(out) == {"V3"}, out
    assert "$" in out
    assert "zh-cn" in out
    assert "default convention" in out


# --- V4 claim evidence gap --------------------------------------------------

def test_v4_missing_referenced_image_number():
    code, out, err = _validate("claim-no-evidence.md")
    assert code == 1
    assert _rules(out) == {"V4"}, out
    assert "图3" in out
    assert "claim-no-evidence.md:8" in out   # selling point sits on line 8
    assert "图1" in out and "图2" in out      # existing placements listed


# --- V5 category × scene ----------------------------------------------------

def test_v5_conflict_pair_reported_with_line_anchor():
    code, out, err = _validate("category-scene-mismatch.md")
    assert code == 1
    assert _rules(out) == {"V5"}, out
    assert "category-scene-mismatch.md:9" in out   # scene sits on line 9
    assert "default convention" in out


def test_v5_unknown_scene_word_not_reported():
    code, out, err = _validate("category-scene-unknown.md")
    assert code == 0, out + err
    assert "findings: 0" in out


# --- V6-V9 image specs (need --platform amazon, verified snapshot) ----------

def test_v7_below_minimum_against_amazon():
    code, out, err = _validate("image-spec-mismatch.md",
                               "--platform", "amazon")
    assert code == 1
    assert _rules(out) == {"V7"}, out
    assert "below minimum 500" in out
    assert "G1881" in out            # expected carries the snapshot source


def test_v8_zero_main_images_against_amazon():
    code, out, err = _validate("main-image-count.md",
                               "--platform", "amazon")
    assert code == 1
    assert _rules(out) == {"V8"}, out
    assert ">= 1" in out


def test_v6_unknown_format_mini_brief():
    d = mini_dir("cvb-v6-format")
    (d / "brief.md").write_text(
        "product_name: X\npricing: CNY 1\nsize_chart: s\ncolor_card: c\n"
        "主图 800x800 webp 白底\n", encoding="utf-8")
    code, out, err = run_cli(["validate", str(d), "--platform", "amazon"])
    assert code == 1, out + err
    assert _rules(out) == {"V6"}, out
    assert "webp" in out


def test_v9_nonwhite_background_mini_brief():
    d = mini_dir("cvb-v9-nonwhite")
    (d / "brief.md").write_text(
        "product_name: X\npricing: CNY 1\nsize_chart: s\ncolor_card: c\n"
        "主图 800x800 jpg 浅灰背景\n", encoding="utf-8")
    code, out, err = run_cli(["validate", str(d), "--platform", "amazon"])
    assert code == 1, out + err
    assert _rules(out) == {"V9"}, out


def test_valid_brief_passes_amazon_snapshot():
    code, out, err = _validate("valid-brief.md", "--platform", "amazon")
    assert code == 0, out + err
    assert "findings: 0" in out
    assert "verified, snapshot 2026-09-11" in out


# --- V10 extreme words ------------------------------------------------------

def test_v10_hit_carries_disclaimer():
    code, out, err = _validate("extreme-words.md")
    assert code == 1
    assert _rules(out) == {"V10"}, out
    assert "extreme-words.md:8" in out   # selling point sits on line 8
    assert "not a legal determination" in out


def test_v10_comparative_words_protected():
    code, out, err = _validate("comparative-words.md")
    assert code == 0, out + err
    assert "findings: 0" in out


def test_v10_bare_zui_is_not_a_hit():
    # regression: "最近上新" must NOT fire the 最X pattern (intensity word
    # required) -- batch-1 defect 2
    d = mini_dir("cvb-v10-bare-zui")
    (d / "brief.md").write_text(
        "product_name: X\npricing: CNY 1\nsize_chart: s\ncolor_card: c\n"
        "卖点: 最近上新款式\n", encoding="utf-8")
    code, out, err = run_cli(["validate", str(d)])
    assert code == 0, out + err


def test_v10_selling_point_line_counted_once():
    # regression: a "卖点:" line is a claim, not also a field -- batch-1
    # defect 1 double-report guard
    d = mini_dir("cvb-v10-single-count")
    (d / "brief.md").write_text(
        "product_name: X\npricing: CNY 1\nsize_chart: s\ncolor_card: c\n"
        "卖点: 国家级工艺认证\n", encoding="utf-8")
    code, out, err = run_cli(["validate", str(d)])
    assert code == 1, out + err
    assert _rules(out) == {"V10"}, out
    v10_lines = [ln for ln in out.splitlines()
                 if ln.startswith("V10 ")]
    assert len(v10_lines) == 1, out


# --- verified / unverified platform semantics --------------------------------

def test_unverified_platform_skips_specs_by_default():
    code, out, err = _validate("unverified-platform.md",
                               "--platform", "taobao")
    assert code == 0, out + err
    assert "UNVERIFIED" in out
    assert "findings: 0" in out


def test_unverified_platform_annotates_when_included():
    code, out, err = _validate("unverified-platform.md",
                               "--platform", "taobao",
                               "--include-unverified")
    assert code == 1, out + err
    assert "unverified" in out
    assert "not checkable" in out
    # the annotation must never carry fabricated numbers
    assert "500" not in "".join(ln for ln in out.splitlines()
                                if ln.startswith("V6 "))


# --- report shape -------------------------------------------------------------

def test_no_platform_note_present_without_flag():
    code, out, err = _validate("valid-brief.md")
    assert code == 0
    assert "no --platform given" in out


def test_inventory_lists_placements_and_specs():
    code, out, err = run_cli(["inventory", str(FIXTURES / "valid-brief.md")])
    assert code == 0
    assert "placement" in out
    assert "image-spec" in out
    assert "inventory != risk" in out


def test_inventory_never_affects_exit_code():
    code, out, err = run_cli(["inventory",
                              str(FIXTURES / "no-brief-structure.md")])
    assert code == 0, out + err


def test_json_format_structure():
    code, out, err = _validate("extreme-words.md", "--format", "json")
    assert code == 1
    doc = json.loads(out)
    assert doc["exit_code"] == 1
    assert len(doc["findings"]) == 1
    f = doc["findings"][0]
    assert f["rule"] == "V10"
    assert "not a legal determination" in f["expected"]
    assert doc["platform"] is None
    assert doc["note_no_platform"]
