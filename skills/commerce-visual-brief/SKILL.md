---
name: commerce-visual-brief
description: Validates e-commerce visual brief documents (product photo and design
  requirement sheets) for completeness, internal consistency, and platform image
  spec compliance. Checks required fields (product name, pricing, size chart,
  color cards, compliance declarations), cross-field consistency (price vs
  currency/locale, selling-point claims vs evidence image placements, category vs
  scene settings), declared image specs (dimensions, ratio, format, main-image
  count, whitespace) against built-in platform requirement snapshots, and flags
  extreme-word compliance risks via lexicon matching. Fully offline and
  deterministic; brief text only - does NOT read or analyze image files, does NOT
  generate briefs, does NOT judge ad-law violations (lexicon hits are risk hints
  only), and does NOT predict conversion. Outputs findings with file:line in text
  or JSON, plus an image-placement inventory. Use when a user asks to check an
  e-commerce photo/design brief for missing fields, contradictory specs, or
  platform image-requirement compliance before sending it to a photography or
  design team.
---

# Commerce Visual Brief

对电商视觉 brief（产品拍摄/设计需求单）做确定性校验。离线运行，只读 brief 文本，
不读图片本体，不生成 brief，不做法律定性。

## When to use this skill

满足以下任一场景时触发：

1. 用户要把拍摄/设计需求单发给摄影团队或设计团队，发布前自查材料齐不齐
2. 用户要求检查 brief 的必填字段（产品名、定价、尺码色卡、合规声明）缺项
3. 用户要求核对 brief 里价格与币种/locale 是否自洽
4. 用户要求核对卖点声称与佐证图位是否对应
5. 用户要求核对图片规格声明（尺寸/比例/格式/主图张数/留白）是否符合某平台要求
6. 用户要求提示 brief 里的极限词合规风险
7. 用户要求输出 brief 的图位/规格声明清单
8. 用户在 CI 中对 brief 材料包做发布前巡检

## When NOT to use this skill

以下场景**不**触发本 skill：

1. 用户要求**生成**一份拍摄 brief——本 skill 不做生成；可引导：按
   references/brief-template.md 参照撰写后，回到本 skill 校验（闭环）
2. 用户要求分析图片本体（"这张主图白底干不干净"）——本 skill 只读 brief 文本，
   不读图片文件
3. 用户要求断言某个词"违法"或预估广告审核结果——极限词命中只是风险提示，
   不做法律定性
4. 审计对象是目录站 listing（ai-tool-directory-publisher）、地理声称
   （geo-evidence-audit）、skill 包结构（skill-eval-harness）、来源侧
   （skill-supply-chain-audit）时——各自归位

## Workflow

1. **定位材料**：确定 brief 文件（单文件或目录；目录 = 一个产品的 brief 材料包）。
   支持 md/markdown/txt/html/htm/json/yaml/yml/csv。
2. **运行校验**（确定性，全部发现由脚本产生，平台规格不靠模型现场记忆）：

   ```bash
   python scripts/audit.py validate <path> [--platform amazon]   # 规格校验
   python scripts/audit.py inventory <path>                      # 图位/规格清单
   ```

3. **解读 finding**：逐条报告 `file:line`、规则、字段值与预期；V2–V5 必须把
   推理链（品类词表命中 → 映射约定 → 缺什么）说给用户听；V10 必须带免责声明。
4. **修订闭环**（LLM 层）：按参照模板补齐/修正 brief 后，必须回到第 2 步重新校验。
5. **边界声明**：材料全绿 ≠ 合规审核通过 ≠ 转化保证；图片本体质量不在本 skill 范围。

### 平台规格快照（verified / unverified）

- 内置平台快照：amazon / taobao / tmall / jd / pdd。**verified=true 的条目**
  表示其官方页在 snapshot_date 被直接抓取并逐字读取；**verified=false 的条目
  数值全部留空**（实现阶段无法核实到官方规则中心原文，绝不预写未核实数字）。
- `--platform` 缺省时只跑 V1–V5 与 V10（报告头部有跳过说明）；
  指定 verified 平台（当前仅 amazon）才启用 V6–V9 图片规格校验。
- 指定 unverified 平台默认跳过 V6–V9；`--include-unverified` 显式开启后，
  对其上的规格声明逐条给出 strength=unverified 的"未核实、无法校验"标注
  （诚实标注，不是编造数字）。
- **以平台规范为准，快照会过期**：所有结论附抓取日期与来源
  （见 references/data-provenance.md），平台官方规则页永远是权威。

## Finding format

每条 finding 固定字段（text 格式，与实际输出逐字一致）：

```
V10 brief-b.md:8 [explicit] lexicon hit: 最X
  value: "全网最低价，闭眼入"
  expected: extreme-word risk hint (lexicon hit is a risk hint, not a legal
  determination; check platform rules and applicable law)
```

- 第一行：`规则 文件:行号 [证据强度] 字段/主题`
- `value`：观察到的原文（截断展示）
- `expected`：预期与依据；default_convention 约定逐条标注"是约定，不是事实"；
  V10 的 expected 恒含免责声明。

## Evidence strength

- **explicit**：字面事实（V1、V6–V10）
- **inferred**：跨字段推导（V2–V5），附推理链
- **unverified**：平台快照未核实条目（默认不跑，--include-unverified 开启）
- **未验证**：合规定性、转化效果——一律不做断言

## Boundaries and red lines

- 离线运行，绝不发起网络请求；不读任何图片/二进制文件
- 不生成 brief（校验器，不是生成器）；LLM 层按参照模板撰写后必须回校验
- 极限词命中 ≠ 违法定性（免责声明原文："词表命中是风险提示，不是法律定性；
  请对照平台规则与适用法规"）；品类/场景映射是 default_convention 约定，
  逐条标注
- 平台规格快照会过期；所有结论附"以平台规范为准"与抓取日期
- 清单（inventory）≠ 风险，不计入退出码
- 只报告，不修改用户文件
- 不输出任何性能数字（未实测的性能一律不写）
- 退出码：0 = 干净；1 = 有 finding；2 = 用法或输入错误（含无 brief 结构）

## End-to-end example

以下为真实运行输出逐字拷贝（命令对 `fixtures/e2e-mixed-dir/` 执行）：

```bash
$ python scripts/audit.py validate fixtures/e2e-mixed-dir/ --platform taobao
commerce-visual-brief v0.1.0 validate
platform: taobao (UNVERIFIED, snapshot 2026-09-11) | unverified included: no
briefs parsed: 3 | files skipped (no brief structure): 0
findings: 2
------------------------------------------------------------------------
V1 brief-a.md:1 [explicit] pricing
  value: (missing)
  expected: required field per novera brief baseline (required set is a default convention (see references/rules.md), not a fact)
V10 brief-b.md:8 [explicit] lexicon hit: 最X
  value: "全网最低价，闭眼入"
  expected: extreme-word risk hint (lexicon hit is a risk hint, not a legal determination; check platform rules and applicable law)
------------------------------------------------------------------------
inventory: 0 item(s) (informational: inventory != risk; never affects the exit code)
------------------------------------------------------------------------
summary: 2 finding(s). exit code: 1
```

```bash
$ python scripts/audit.py inventory fixtures/e2e-mixed-dir/
commerce-visual-brief v0.1.0 inventory
platform: (none) | no --platform given: V6-V9 image-spec checks skipped (pass --platform <slug> to enable)
briefs parsed: 3 | files skipped (no brief structure): 0
findings: 0
------------------------------------------------------------------------
------------------------------------------------------------------------
inventory: 3 item(s) (informational: inventory != risk; never affects the exit code)
  placement brief-a.md:8 图1: 展开状态展示
  placement brief-b.md:9 图1: 产品正面展示
  placement brief-clean.md:11 图1: 正面白底展示
------------------------------------------------------------------------
summary: 0 finding(s). exit code: 0
```

注意上例同时演示了 unverified 平台行为：taobao 快照未核实（UNVERIFIED），
报告头部如实标注，V6–V9 静默跳过；`--include-unverified` 开启后才会对
未核实条目给出"未核实、无法校验"的标注 finding。
