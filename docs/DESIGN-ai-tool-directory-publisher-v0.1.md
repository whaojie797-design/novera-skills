# ai-tool-directory-publisher v0.1.0 完整设计

> 设计人：软件架构师（高见远）
> 状态：设计稿，待用户核对 §1「解读假设」后定稿
> 所属：novera-skills mono-repo 第 2 款 skill（`skills/ai-tool-directory-publisher/`）
> 前序：geo-evidence-audit v0.1.0 已发布（tag geo-evidence-audit-v0.1.0），本设计复用其骨架惯例
> 本文档是设计，不含实现代码；文中代码块均为草案签名与格式约定。

---

## 1. 解读假设（供用户逐条核对纠偏）

原始提示词全文丢失，以下为本设计对名称 "ai-tool-directory-publisher"（AI 工具目录发布器）的语义重构。**每条都可能被用户推翻，推翻后按 §11 修订流程更新设计。**

| # | 假设 | 依据与范围取舍 |
|---|------|---------------|
| A1 | 核心定位：帮助把一个 AI 工具/产品的 listing 材料提交到各 AI 工具目录站。脚本负责**提交材料完整性校验、多目录一致性审计、提交状态跟踪**三件事，不替用户执行提交 | 任务背景明确红线"不自动提交"（跨站提交需账号与人工确认）；确定性脚本做不了登录态提交 |
| A2 | **不爬目录站、不联网**。各目录站的字段要求是内置快照数据（抓取日期 + 来源 URL + 证据强度），放 `scripts/directory_data.py` 纯数据模块（复用 geo_data.py 模式），并全程标注"以官网为准" | 全局硬约束"确定性脚本优先"；目录站字段要求经常变，快照数据必须诚实标注时效性 |
| A3 | 覆盖目录站 v0.1 收敛为 6 家：Futurepedia、Toolify、There's An AI For That、AI Tools Directory、TopAI.tools、AITools.fyi。每家的具体字段上限数字在**实现阶段逐家到官网核实后填入**，设计阶段一律不预写数字（硬约束：不编数字） | 6 家是用户建议方向中点名的 + 知名度最高的；字段数值留白是诚实文档红线的直接要求 |
| A4 | 输入格式：listing 文件支持 JSON / YAML / Markdown（含 YAML frontmatter）；状态表支持 CSV / JSON。单文件或目录两种输入模式 | 与 mono-repo 既有资产惯例对齐；目录模式支持"一个目录 = 一个工具的全套提交包" |
| A5 | 校验字段集：name、tagline、description、category、pricing、features、url、screenshot。校验维度：必填缺失、长度区间、枚举合法性（pricing）、URL 格式、截图规格声明 | 任务建议方向的字段清单；category 枚举以 directory_data.py 快照为准 |
| A6 | 一致性审计（cross-listing diff）以**工具核心事实**为锚：name、url、pricing、version 四项在不同目录 listing 间不一致 → finding。description 漂移只在"明显过期"（如内嵌旧版本号、旧 pricing 字样）时报，不做语义级 diff | 离线确定性脚本做不了语义相似度；字面可判的先做，宁漏报不误报 |
| A7 | 提交状态表字段：tool、directory、status、date、notes。status 枚举：draft / submitted / under-review / listed / rejected；date 为 ISO 8601 | 任务建议"structured 状态表"；枚举覆盖提交生命周期全阶段 |
| A8 | 红线三条写入 SKILL.md：①不自动提交 ②不爬目录站 ③不承诺收录（"提交 ≠ 收录"，材料全绿只是可提交，结果由目录站决定） | 任务背景 + 诚实文档红线 |
| A9 | CLI 退出码语义遵循全局规范：0=干净、1=有 finding/issue、2=用法或输入错误 | 组织硬约束 |
| A10 | 检测目标语言：中英文 listing 均可（长度校验按字符数，不做双语词表） | 字段长度限制与语言无关；语义类检测（A6）只做字面模式 |
| A11 | 材料裁剪/格式转换（如把长 description 裁到各站上限）由 LLM 层按 SKILL.md 指引完成，脚本只校验不改写 | 确定性脚本不做文案改写；改写后必须回到脚本重新校验，形成闭环 |
| A12 | 与 geo-evidence-audit 的边界：本款管 listing **材料与一致性**；listing 里若含地理声称（如"上海办公室"与 +1 电话矛盾），那是 geo-evidence-audit 的职责，本款不做地理交叉检测。边界写入 `references/scope.md` | 与首款互补不重叠（组织硬约束） |

---

## 2. 功能范围

### 2.1 三大功能与规则编号

| 功能 | 规则 ID | 名称 | 逻辑 | finding 强度 |
|------|---------|------|------|-------------|
| 材料校验 | V1 | missing-required-field | 目录快照中标记 required 的字段缺失 | explicit |
| 材料校验 | V2 | field-length-out-of-range | 字段长度超出该目录快照的 min/max 区间 | explicit |
| 材料校验 | V3 | invalid-enum | pricing 不在枚举（free/freemium/paid/subscription）、category 不在快照枚举 | explicit |
| 材料校验 | V4 | invalid-url | url 字段非 http(s) 绝对地址、含空格、缺 scheme | explicit |
| 材料校验 | V5 | screenshot-spec-mismatch | 截图声明的尺寸/格式与目录快照规格不符 | explicit |
| 一致性 | C1 | cross-listing-drift | name/url/pricing/version 四锚点在不同目录 listing 间不一致 | inferred（附对比值） |
| 状态表 | S1 | status-table-integrity | 非法 status 枚举、date 缺失或非 ISO 8601、listing 文件存在但状态表无记录 | explicit |

反例保护（不触发）：description 长度落在区间内但措辞不同的多目录 listing、pricing 大小写差异（Free vs free，归一化后一致）、状态表里合理的重复提交记录（rejected → resubmitted）、空 features 列表（部分目录允许）。

### 2.2 证据强度模型（对齐首款）

| 强度 | 定义 |
|------|------|
| explicit | 直接对照单条规则得出（V1–V5、S1） |
| inferred | 由跨文件对比推导（C1，finding 必须附两侧 file:line 与字段值） |
| unverified | directory_data.py 快照中尚未到官网核实过的字段要求——此类校验**默认不跑**，需 `--include-unverified` 显式开启，报告标注"未验证" |
| 未验证 | 任何关于"该工具是否会被目录站收录"的判断——skill 一律不做断言 |

> 快照数据时效性：每个目录站的字段要求随时间变化，所有基于快照的 finding 结论均附带"以官网为准"声明（落点在 references/data-provenance.md）。

---

## 3. SKILL.md 全文草案（约 190 行，< 500 行门禁内）

````markdown
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
  expected: <= 60 chars per futurepedia snapshot (2026-08-30, see data-provenance)
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
  expected: required per futurepedia snapshot (2026-08-30, see data-provenance)
[finding] fixtures/submit-pack/toolify.yaml:11  rule=V3  strength=explicit
  field:    pricing
  value:    "free-tier"
  expected: one of free/freemium/paid/subscription per toolify snapshot (2026-08-30)
2 findings. exit code: 1
```
````

---

## 4. agents/openai.yaml 草案

```yaml
# 跨客户端兼容描述。触发场景集合必须与 SKILL.md description 等价（措辞可不同）。
name: ai-tool-directory-publisher
version: 0.1.0
description: >
  Offline, deterministic auditor for AI tool directory submission materials.
  Validates listing files (JSON/YAML/Markdown) against per-directory requirement
  snapshots (Futurepedia, Toolify, There's An AI For That, AI Tools Directory,
  TopAI.tools, AITools.fyi): required fields, length limits, pricing/category
  enums, URL format, screenshot specs. Audits cross-directory consistency of the
  same tool's listings (name/url/pricing/version drift). Tracks submission status
  in a structured CSV/JSON table. Does NOT auto-submit, does NOT crawl directory
  sites, does NOT guarantee acceptance, and requires manual submission by the user.
when_to_use:
  - Prepare an AI tool for submission to AI tool directories
  - Validate listing materials against a directory's field requirements
  - Find contradictions between the same tool's listings on different directories
  - Generate a missing-materials checklist before submission
  - Maintain and validate a submission status tracker (submitted/under-review/listed/rejected)
when_not_to_use:
  - Auto-submitting to directories (manual submission only)
  - Crawling or scraping directory sites
  - Auditing geographic claims inside listings (use geo-evidence-audit)
  - Guaranteeing listing acceptance or SEO improvement
cli:
  entry: scripts/audit.py
  runtime: python3
  subcommands: [validate, diff, status]
  exit_codes:
    0: no findings
    1: findings present (validation issues, drift, or status-table problems)
    2: usage or input error
```

---

## 5. scripts/ 模块清单（纯标准库）

### 5.1 模块划分

| 模块 | 职责 | 关键函数签名（草案） |
|------|------|---------------------|
| `audit.py` | CLI 入口 + 编排，三个子命令 validate/diff/status | `main(argv: list[str]) -> int`<br>`cmd_validate(args) -> int` / `cmd_diff(args) -> int` / `cmd_status(args) -> int` |
| `listing.py` | listing 解析：JSON / YAML（标准库手写最小解析：仅支持扁平键值 + 一层列表，复杂 YAML 报"未支持"）/ Markdown frontmatter 与 H2 字段；输出带行号的 Listing 对象 | `parse_listing(text: str, path: str) -> Listing \| None`<br>`@dataclass Listing: path, fields: dict[str, FieldValue]`<br>`@dataclass FieldValue: value, line` |
| `directory_data.py` | 纯数据模块（复用 geo_data.py 模式）：6 家目录站的字段要求快照。每条记录含 source_url、snapshot_date、verified 布尔（实现阶段官网核实后置 true）；未核实条目默认不参与校验 | `DIRECTORIES: dict[str, DirectorySpec]`<br>`@dataclass DirectorySpec: slug, name, source_url, snapshot_date, verified, fields: dict[str, FieldSpec]`<br>`@dataclass FieldSpec: required, min_len, max_len, enum, screenshot_spec, verified` |
| `checkers.py` | V1–V5 材料校验 + C1 一致性 diff + S1 状态表校验 | `run_validate(listings: list[Listing], spec: DirectorySpec, include_unverified: bool) -> list[Finding]`<br>`run_diff(listings: list[Listing]) -> list[Finding]`<br>`run_status(rows: list[StatusRow], listing_paths: list[str]) -> list[Finding]`<br>`@dataclass StatusRow: tool, directory, status, date, notes, line` |
| `report.py` | 文本/JSON 双格式渲染，finding 排序（文件、行号） | `render_text(findings: list[Finding]) -> str`<br>`render_json(findings: list[Finding], notes: list[str]) -> dict`<br>`@dataclass Finding: file, line, rule, strength, field, value, expected` |

依赖方向：`audit.py → {listing, checkers, report} → directory_data`。禁止反向依赖。

### 5.2 CLI 参数设计

```
usage: python audit.py <subcommand> ...

validate PATH [--directory SLUG] [--include-unverified] [--format {text,json}]
              [--output FILE] [--exclude GLOB] [--quiet]
  PATH          单文件或目录（目录 = 提交包，按文件名/内含 slug 匹配目录站）
  --directory   只按指定目录站校验；缺省 = 对快照中所有 verified 目录各跑一遍
diff FILE1 FILE2 [...] [--format ...] [--quiet]
  2 个及以上 listing 文件，比对 name/url/pricing/version 四锚点
status TABLE [--format ...] [--quiet]
  TABLE         提交状态表（CSV/JSON）
```

通用约定：

- `--include-unverified`：开启快照中 verified=false 条目的校验，报告逐条标注"未验证"；
- 无 finding 时输出 `0 findings`，退出 0；
- 输入中检测不到任何 listing 结构（validate）或状态表行数为 0（status）→ 退出 2；
- 路径不存在 / 参数不合法 / diff 少于 2 个文件 → 退出 2。

### 5.3 退出码语义表

| 退出码 | 语义 | 触发条件 |
|--------|------|---------|
| 0 | 干净/通过 | 无任何 finding |
| 1 | 有 finding | V1–V5 / C1 / S1 至少一条；含 `--include-unverified` 开启后的未验证条目 |
| 2 | 用法或输入错误 | 参数不合法、路径不存在、无 listing 结构、状态表为空。优先级 2 > 1 > 0 |

---

## 6. references/ 文档清单

| 文件 | 内容 |
|------|------|
| `data-provenance.md` | 6 家目录站快照的来源：每家附官网 URL + 抓取日期 2026-08-30 + 证据强度（实现阶段逐家核实后从"未验证"升级为 explicit/inferred，未核实的一律保持"未验证"且默认不参与校验）。**全文显著位置声明：目录站字段要求随时可能变化，一切以官网为准** |
| `rules.md` | V1–V5 / C1 / S1 精确判定逻辑、反例保护清单（§2.1）、已知局限（不做语义 diff、YAML 只支持最小子集） |
| `evidence-model.md` | 证据强度四档定义、快照 verified 标志与 `--include-unverified` 的关系、"材料全绿 ≠ 收录"说明 |
| `scope.md` | 与相邻 skill 分工：**geo-evidence-audit**（管 listing 内地理声称，本款不做）、**skill-sentry**（本地运行时审计）、**skill-supply-chain-audit**（来源侧供应链画像）；本款只管 listing 材料校验、跨目录一致性、提交状态 |

不创建 README / CHANGELOG / 安装指南（硬约束：进根 README）。

---

## 7. fixtures/ 清单（15 项，全部用 Write 工具逐个写）

| # | 文件 | 场景 | 预期退出码 | 预期 finding 数 |
|---|------|------|-----------|----------------|
| 1 | `valid-listing.json` | 字段齐全、长度/枚举/URL 全合规（针对 verified 目录） | 0 | 0 |
| 2 | `valid-listing.yaml` | 同上，YAML frontmatter 格式 | 0 | 0 |
| 3 | `missing-tagline.json` | 缺 required 字段 tagline | 1 | 1（V1） |
| 4 | `tagline-too-long.json` | tagline 超上限（上限值以实现阶段快照为准，夹具按超限构造） | 1 | 1（V2） |
| 5 | `bad-pricing.json` | pricing 为 `free-tier`（非枚举值） | 1 | 1（V3） |
| 6 | `bad-url.json` | url 缺 scheme（`example.com/tool`） | 1 | 1（V4） |
| 7 | `screenshot-spec.md` | 截图声明尺寸与快照规格不符 | 1 | 1（V5） |
| 8 | `valid-pack/`（目录） | 同一工具 × 3 个目录 listing，四锚点一致 | 0 | 0 |
| 9 | `pricing-drift-pack/`（目录） | 两 listing pricing 一写 free 一写 paid | 1 | 1（C1） |
| 10 | `version-drift-pack/`（目录） | 两 listing version 漂移（1.2.0 vs 1.3.0） | 1 | 1（C1） |
| 11 | `status-valid.csv` | 6 行状态记录，枚举/日期全合法 | 0 | 0 |
| 12 | `status-bad.csv` | 含非法 status 枚举 + 缺 date 两处问题 | 1 | 2（S1） |
| 13 | `no-listing-structure.md` | 纯随笔文本，无任何 listing 字段结构 | 2 | —（输入错误） |
| 14 | `empty.txt` | 空文件（合法输入，无事可审） | 0 | 0 |
| 15 | `e2e-mixed-dir/`（目录） | 内含 #3、#5 与一个合规 listing + status.csv | 1 | 2 |

边界夹具补充（并入 #8 或 #15 内）：`case-diff-pack/`（Free vs free 大小写差异——C1 反例保护，0 finding）、`rejected-resubmitted.csv`（rejected → resubmitted 记录——S1 反例保护，0 finding）。

> 注：长度/枚举具体数值在实现阶段以 directory_data.py 快照为准构造夹具，上表"预期 finding 数"是设计目标，以实际运行为准校准，偏离需在 PR 说明。

---

## 8. 测试矩阵（8 触发 + 4 非触发 + 1 端到端）

### 8.1 触发测试（T1–T8）

| ID | 用户输入（示意） | 预期行为 |
|----|----------------|---------|
| T1 | "帮我把这个 AI 工具提交到 Futurepedia，先检查材料齐不齐" | 触发；validate + 缺失清单 |
| T2 | "检查我的 listing 是否符合 Toolify 的字段要求" | 触发；validate --directory toolify |
| T3 | "对比我在两个目录的 listing 是否信息一致" | 触发；diff |
| T4 | "生成提交清单，看看还缺哪些材料" | 触发；validate 输出按字段归组的缺口清单 |
| T5 | "维护一张提交状态表并校验它" | 触发；status |
| T6 | "我的 pricing 在两个目录写的不一样，帮我找矛盾" | 触发；diff（C1） |
| T7 | "截图规格符合各目录站要求吗" | 触发；validate（V5） |
| T8 | "给我各目录站提交要求的对照表" | 触发；基于 directory_data.py 快照输出对照表（附以官网为准声明） |

### 8.2 非触发测试（N1–N4）

| ID | 用户输入（示意） | 预期行为 |
|----|----------------|---------|
| N1 | "自动帮我把工具提交到所有目录站" | 不触发自动提交；红线响应：引导先做材料校验，提交需人工 |
| N2 | "爬取 Futurepedia 的目录数据" | 不触发（不爬站红线） |
| N3 | "审计这个工具落地页的地理信息是否自洽" | 不触发（geo-evidence-audit 职责） |
| N4 | "保证我的工具一定被收录" | 不触发（不承诺收录红线，如实拒绝） |

### 8.3 端到端测试（E1）

对 `fixtures/e2e-mixed-dir/` 完整走一遍：validate 断言退出码 = 1、finding 数 = 2（V1 + V3）、每条含 file:line 与"以官网为准"提示；status 子命令对该目录内 status.csv 断言退出 0；diff 对两个合规 listing 断言退出 0；JSON 模式可解析且字段齐全。

### 8.4 脚本级单元测试（CI 矩阵执行）

- fixtures #1–#14 全量跑：预期退出码逐一断言（预期 exit 1 的用例一律 `if` 包裹）；
- `--directory slug` 过滤：对 #3 断言只在对应目录站规则下报 V1；
- `--include-unverified`：对含未核实条目的构造夹具断言默认 0 finding、开启后报"未验证"finding；
- 退出码 2：不存在路径、diff 只给 1 个文件、#13 无 listing 结构、空状态表；
- 反例保护：`case-diff-pack/`、`rejected-resubmitted.csv` 断言 0 finding。

### 8.5 CI 写法强制约定

```bash
# 预期 exit 1 的唯一允许写法（if 包裹 + 成功则显式失败）
if python skills/ai-tool-directory-publisher/scripts/audit.py validate skills/ai-tool-directory-publisher/fixtures/missing-tagline.json > /dev/null; then
  echo "::error::expected exit 1, got 0"; exit 1
fi
# 注意：不允许 `|| true`（会把 exit 2 也吞成"通过"）
```

---

## 9. 硬约束核对清单（本 skill 设计 × 全局 10 条）

| 约束 | 落位 |
|------|------|
| 纯标准库零依赖，3.9+ | §5.1 全部标准库；YAML 走最小子集手写解析而非引入 PyYAML；CI py39 门禁 |
| 退出码 0/1/2 | §5.3 |
| finding 带 file:line | §2.1 / §3 Finding format / §8.3 断言 |
| 性能数字不预写 | 全文无性能声明；SKILL.md 红线显式禁止 |
| 外部事实 URL + 日期 + 证据强度 | §6 data-provenance.md（6 站快照逐家附 URL + 抓取日期 2026-08-30 + 强度 + "以官网为准"） |
| 目录结构四件套 | SKILL.md + agents/openai.yaml + scripts/ + references/ + fixtures/ |
| SKILL.md < 500 行 | §3 约 190 行，CI wc -l 门禁 |
| 确定性脚本优先 | §3 Workflow 第 2 步："不靠模型现场记忆各站字段要求" |
| 诚实文档红线 | §2.2 unverified 默认不跑；§2.1/A3 字段数值留待官网核实，不预写；§7 夹具预期以实际运行为准 |
| 预期 exit 1 用 if 包裹 | §8.5 |
| 夹具用 Write 工具逐个写 | §7 标注（实现阶段执行） |
| 目录数据纯数据模块 | §5.1 directory_data.py（复用 geo_data.py 模式） |

---

## 10. 待用户确认项汇总

1. §1 解读假设 A1–A12 逐条核对（尤其是 A2 不爬站不联网、A6 一致性只比四锚点不做语义 diff、A11 裁剪由 LLM 层做且必须回校验）；
2. A3 的 6 家目录站清单是否需增删；
3. A7 状态枚举五档是否够用（是否需要 paused / archived）；
4. §7 夹具"预期 finding 数"是否认可作为验收基线。

确认后进入实现阶段（Task #5 之后的排期由 team-lead 决定）。
