# -*- coding: utf-8 -*-
"""platform_specs.py - pure data module: per-platform image spec snapshots.

Family convention (verified/unverified, from ai-tool-directory-publisher):
- verified=True means "the official page listed in source_url was fetched on
  snapshot_date and the fields below were read from its text". It does NOT
  mean the values are permanently current - snapshots age; the platform is
  always authoritative ("以平台规范为准").
- Unverified entries carry verified=False and EMPTY numeric fields. They
  never participate in V6-V9 by default; --include-unverified only adds an
  explicit "unverified, not checkable" annotation (never fabricated numbers).
- Fields that the fetched page does not state are left as None - never
  inferred, never defaulted.

Snapshot status (fetched 2026-09-11, see references/data-provenance.md):
- amazon: verified (official help page G1881 fetched directly)
- taobao / tmall / jd / pdd: verified=False (official rule-center pages not
  directly reachable; only encyclopedia/third-party references found, so no
  numbers are recorded per the honesty red line).
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass
class PlatformSpec:
    slug: str
    name: str
    source_url: str
    snapshot_date: str
    verified: bool
    # empty tuple = not stated on the fetched page (never guessed)
    formats: Tuple[str, ...] = ()
    min_long_side: Optional[int] = None
    max_long_side: Optional[int] = None
    recommended_long_side: Optional[int] = None
    # (min, max); None component = that bound not stated
    main_image_count: Optional[Tuple] = None
    ratio: Optional[str] = None
    product_fills_percent: Optional[int] = None
    whitespace_required: Optional[bool] = None
    reference_notes: str = ""


PLATFORMS = {
    "amazon": PlatformSpec(
        slug="amazon",
        name="Amazon Seller Central",
        source_url=("https://sellercentral.amazon.com.mx/help/hub/reference/"
                    "external/G1881"),
        snapshot_date="2026-09-11",
        verified=True,
        formats=("jpg", "jpeg", "tif", "tiff", "png", "gif"),
        min_long_side=500,
        max_long_side=10000,
        recommended_long_side=1000,
        main_image_count=(1, None),   # "at least one compliant main image"
        ratio=None,                    # not stated as a hard requirement
        product_fills_percent=85,      # "Show the product as 85% of the image"
        whitespace_required=True,      # pure white background RGB 255,255,255
        reference_notes=("Official help page 'Product image guide' (G1881) "
                         "fetched directly. Formats: JPEG/TIFF/PNG/"
                         "non-animated GIF (JPEG recommended). Size: 500-"
                         "10000 px longest side; 1000+ enables zoom; 72 dpi; "
                         "RGB preferred. MAIN: pure white background RGB "
                         "255,255,255; product 85% of image; no hard image-"
                         "count ceiling stated (at least one MAIN required)."),
    ),
    "taobao": PlatformSpec(
        slug="taobao",
        name="Taobao",
        source_url="",
        snapshot_date="2026-09-11",
        verified=False,
        formats=(),
        reference_notes=("Official rule-center page not reachable during "
                         "implementation; only the Taobao encyclopedia "
                         "(bk.taobao.com, official domain but not the rule "
                         "center) was found, so per the honesty red line NO "
                         "numbers are recorded. Skipped by default; "
                         "--include-unverified only annotates."),
    ),
    "tmall": PlatformSpec(
        slug="tmall",
        name="Tmall",
        source_url="",
        snapshot_date="2026-09-11",
        verified=False,
        formats=(),
        reference_notes=("Same status as taobao: encyclopedia pages only "
                         "(bk.taobao.com), no rule-center original; no "
                         "numbers recorded."),
    ),
    "jd": PlatformSpec(
        slug="jd",
        name="JD.com (main marketplace)",
        source_url="",
        snapshot_date="2026-09-11",
        verified=False,
        formats=(),
        reference_notes=("Main-site rule pages not reachable; the official "
                         "jddj.com rule center found belongs to JD Shangou "
                         "(instant retail), a different business line, so it "
                         "is not used as the main-site baseline. No numbers "
                         "recorded."),
    ),
    "pdd": PlatformSpec(
        slug="pdd",
        name="Pinduoduo",
        source_url="",
        snapshot_date="2026-09-11",
        verified=False,
        formats=(),
        reference_notes=("Only third-party articles found (750x750, JPG/PNG "
                         "claims vary between sources); no official page "
                         "reached. No numbers recorded."),
    ),
}


def get_platform(slug):
    """Return (PlatformSpec, None) or (None, error-message)."""
    spec = PLATFORMS.get(slug)
    if spec is None:
        return None, ("unknown platform slug: %s (valid: %s)"
                      % (slug, ",".join(sorted(PLATFORMS))))
    return spec, None
