---
name: ai-tool-directory-publisher
description: Prepares and audits AI tool listing materials for AI tool directories
  (Futurepedia, Toolify, There's An AI For That, and more). Validates field
  completeness, length limits, pricing/category enums, URLs, and screenshot specs
  against per-directory requirement snapshots; audits consistency of the same tool's
  listings across directories (name/url/pricing/version drift); tracks submission
  status in a structured table. Offline and deterministic. Use when the user asks to
  prepare directory submissions, check listing materials against directory
  requirements, find contradictions between listings on different directory sites, or
  maintain a submission status tracker. Does NOT auto-submit, does NOT crawl directory
  sites, and does NOT guarantee listing acceptance.
---

# AI Tool Directory Publisher

为 AI 工具目录站准备与审计提交材料。确定性脚本离线完成全部校验，不联网、不爬站、不自动提交。

## When to use this skill

满足以下任一场景时触发：

1. 用户要把 AI 工具提交到目录站（Futurepedia / Toolify / There's An AI For That 等），先检查材料齐不齐
2. 用户要求校验 listing 是否符合某个目录站的字段要求（长度、枚举、URL、截图规格）
3. 用户要求对比同一工具在不同目录站的 listing 是否信息一致（pricing 矛盾、版本漂移）
4. 用户要求生成一份"还缺哪些材料"的提交清单
5. 用户要维护或校验提交状态表（已提交/待审/已收录/被拒 + 日期）
6. 用户给出截图规格，要求核对是否符合各目录站要求
7. 用户要求输出各目录站提交要求的对照表
8. 用户在 CI 中对 listing 材料包做发布前巡检

## When NOT to use this skill

以下场景**不**触发本 skill：

1. 用户要求**自动**把工具提交到目录站——本 skill 不自动提交（需要账号与人工确认），
   只做材料准备与校验；可引导用户先跑材料校验再人工提交
2. 用户要求爬取目录站数据、抓取竞品 listing——本 skill 不爬站、不联网
3. 用户要求核实或审计 listing 里的地理信息（办公室地址、电话区号矛盾）——
   这是 geo-evidence-audit 的职责
4. 用户要求保证工具被收录、提升排名——本 skill 不承诺收录，不提供 SEO 服务

## Workflow

1. **定位材料**：确定 listing 文件（单文件或目录；目录 = 一个工具的提交包）。
2. **运行校验**（确定性，全部发现由脚本产生，不靠模型现场记忆各站字段要求）：

   ```bash
   python scripts/audit.py validate <path>                 # 材料校验
   python scripts/audit.py diff <file1> <file2> [...]      # 跨目录一致性
   python scripts/audit.py status <status.csv>             # 状态表校验
   ```

3. **裁剪材料**（LLM 层）：对超出某站上限的字段按该站要求裁剪或改写，改写后必须
   回到第 2 步重新校验，形成闭环。
4. **解读 finding**：逐条报告 `file:line`、规则、字段值与预期；基于快照数据的结论
   必须附带"以官网为准"提示。
5. **边界声明**：向用户明确——材料全绿 ≠ 收录；提交由用户人工完成。

## Finding format

每条 finding 固定字段：

```
[finding] file:line  rule=V2  strength=explicit
  field:    tagline
  value:    "The best AI writing assistant for teams and enterprises ..." (78 chars)
  expected: <= 60 chars per futurepedia snapshot (2026-09-10, see data-provenance)
```

## Evidence strength

- **explicit**：对照单条规则直接得出（V1–V5、S1）
- **inferred**：跨文件对比推导（C1，附两侧 file:line 与字段值）
- **unverified**：快照中未到官网核实的字段要求——默认不跑，`--include-unverified` 开启
- **未验证**：目录站是否会收录本工具——一律不做断言

## Boundaries and red lines

- 不自动提交、不爬目录站、不承诺收录（三条红线，无例外）
- 离线运行，绝不发起网络请求
- 各站字段要求是快照数据，会过期；所有结论附"以官网为准"
- 只校验与报告，不修改用户文件；文案裁剪由 LLM 层完成并回校验
- 不输出任何性能数字（未实测的性能一律不写）
- 退出码：0 = 干净；1 = 有 finding；2 = 用法或输入错误（含输入中无 listing 结构）

## End-to-end example

```bash
$ python scripts/audit.py validate fixtures/submit-pack/
[finding] fixtures/submit-pack/futurepedia.json:4  rule=V1  strength=explicit
  field:    tagline
  value:    (missing)
  expected: required per futurepedia snapshot (2026-09-10, see data-provenance)
[finding] fixtures/submit-pack/toolify.yaml:11  rule=V3  strength=explicit
  field:    pricing
  value:    "free-tier"
  expected: one of free/freemium/paid/subscription per toolify snapshot (2026-09-10)
2 findings. exit code: 1
```
