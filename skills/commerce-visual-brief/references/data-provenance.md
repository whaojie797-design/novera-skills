# Data provenance - commerce-visual-brief

所有内置数值的来源、抓取日期与证据强度。**以平台规范为准，快照会过期**：
平台官方规则页永远是权威，本文件的快照只是实现日期的切片。

## 1. 平台图片规格快照（platform_specs.py）

抓取方式：每平台至多 1 次官方域页面直接抓取（WebFetch，2026-09-11）。
核实标准 = 平台官方规则/帮助中心原文可直接抓取并逐字读取。
核实不到 → `verified=false`，数值字段全部留空，绝不预写未核实数字。

### amazon（verified=true）

- 来源 URL：https://sellercentral.amazon.com.mx/help/hub/reference/external/G1881
  （Amazon Seller Central 官方帮助页 "Product image guide"）
- snapshot_date：2026-09-11
- 证据强度：verified —— 官方页直接抓取成功，以下数值逐字读自该页文本：
  - 格式：JPEG / TIFF / PNG / 非动画 GIF（JPEG 推荐）
  - 尺寸：最长边 500–10000 px；1000 px 以上启用缩放（zoom）；72 dpi；RGB 首选
  - 主图（MAIN）：纯白背景 RGB(255,255,255)；产品占图片 85%；至少 1 张合规主图，
    页面未给出张数上限（快照记 main_image_count=(1, None)）

### taobao / tmall（verified=false）

- 未核实原因：仅找到淘宝百科页（bk.taobao.com，官方域但**不是规则中心**），
  规则中心原文在实现阶段不可直接抓取；第三方页面数值互相矛盾。
- 处置：数值全部留空；默认不参与 V6–V9；`--include-unverified` 开启后仅出
  "未核实、无法校验"的标注，不产出任何校验结论。

### jd（verified=false）

- 未核实原因：主站规则页不可达；实现阶段找到的 jddj.com 规则中心属于
  京东秒送（即时零售）业务线，不是主站基线，故不采用。

### pdd（verified=false）

- 未核实原因：仅第三方文章（750x750、JPG/PNG 说法不一），无官方页抓取成功。

## 2. 极限词表（brief_data.py EXTREME_WORDS）

- 范围声明：中文为主（最X / 第一 / 顶级 / 国家级 / 全网最低 / 绝对 / 唯一 /
  根治类功效等 8 个模式），英文为辅（best / miracle / guaranteed results 等
  平台通用禁用模式）。词表是**保守的字面匹配**：宁漏报不误报。
- 来源：依据中国《广告法》第九条禁用的"国家级、最高级、最佳"类绝对化用语
  的公开表述整理的常见模式，不是法律文本本身，也不是完整清单。
- **词表命中 ≠ 违法**：命中仅是风险提示，逐条附免责声明
  （"词表命中是风险提示，不是法律定性；请对照平台规则与适用法规"）。
  比较类措辞（"更耐用 / 较上一代提升"）有反例保护，不触发。
- 词表标记 default_convention：是约定，不是事实；可按用户/平台要求调整。

## 3. 约定表（brief_data.py 其余映射）

REQUIRED_FIELDS（4 必填字段）、CATEGORY_DECLS（6 品类必需声明）、
CATEGORY_SCENE_CONFLICTS（3 组品类×场景冲突对）、CURRENCY_LOCALE（币种-locale
对应表）均为 **default_convention**：novera brief 基线的起草约定，
不是任何平台或法规的事实断言；报告逐条标注。
