# skill-supply-chain-audit v0.1.0 完整设计

> 设计人：软件架构师（高见远）
> 状态：设计稿，待用户核对 §1「解读假设」后定稿
> 所属：novera-skills mono-repo 第 4 款 skill（`skills/skill-supply-chain-audit/`）
> 前序：geo-evidence-audit / ai-tool-directory-publisher / skill-eval-harness v0.1.0 均已发布；本设计复用三者沉淀的骨架惯例（纯数据模块、verified/unverified、子命令式 CLI、SARIF 为新增输出格式）
> 本文档是设计，不含实现代码；文中代码块均为草案签名与格式约定。

---

## 1. 解读假设（供用户逐条核对纠偏）

原始提示词全文丢失，以下为本设计对名称 "skill-supply-chain-audit"（Skill 供应链审计）的语义重构。**每条都可能被用户推翻，推翻后按 §10 修订流程更新设计。**

| # | 假设 | 依据与范围取舍 |
|---|------|---------------|
| A1 | 核心定位：**来源侧供应链画像**——回答"这个包从哪来、谁维护、分发链路风险如何"。用户拍板的差异化子集：skill-sentry 回答"包里有没有恶意代码"（本地运行时），eval-harness 回答"包内结构质量现状"，本款只管**来源与分发** | 任务背景显式定位；边界写入 references/scope.md |
| A2 | **不联网**。来源侧数据全部来自**用户提供的快照输入**：①gh api 导出 JSON（repo 元数据 / commits / contributors / releases，用户自行执行 `gh api` 后交给脚本）②git remote URL 文本（`git remote -v` 输出或 .git/config 摘录）③skill 市场页面 HTML 存档。脚本解析快照，不发起任何网络请求 | 任务背景建议方向；联网是三条红线之一 |
| A3 | 仓库健康度画像（profile 子命令）基于快照推导：最后提交时点、维护者/贡献者数、commit 频率窗口、release 节奏、open issue 比例、archived/fork 标志。**时间基准优先取快照内的 `fetched_at` 字段**（保证可复现）；快照无该字段时用系统当前日期并在报告显式标注"以本机日期为基准，未验证" | 可复现性要求；相对时间判断必须有锚点，锚点本身要诚实标注 |
| A4 | 健康度阈值（如"最后提交超 N 天视为 stale"）作为**可配置默认值**随规则数据模块发布，草案默认值在实现阶段与用户确认后定稿；报告中逐项标注"阈值 X 为默认约定，非事实断言" | 阈值是约定不是事实，必须与"实测数字"严格区分——诚实文档红线 |
| A5 | 引用面清单（refs 子命令）：提取 SKILL.md / references/ 中的外部 URL、scripts 字符串字面量中的端点（复用 harness 式 AST 思路但**只列清单不定性**）、agents/openai.yaml 中的外部引用。**清单本身不改变退出码**；仅对可判定问题（明文 http:// 端点、字面量 IP 直连端点等）出 finding | "清单"与"finding"分离，避免把信息性内容误当问题 |
| A6 | 分发链风险清单（chain 子命令）：①安装方式暴露面——文档中 `curl … \| sh`、`pip install <name>`、`npm install -g` 等提示语模式检测；②品牌仿冒信号——候选名与内置知名 skill 名清单做相似度比较（编辑距离类算法，阈值草案默认值同 A4 处理），含连字符省略/复数/拼写变体等 typosquat 模式 | 任务建议方向；相似度阈值同样是"默认约定"需标注 |
| A7 | SARIF 2.1.0 输出（用户点名）：作为 `--format sarif` 第三种输出格式与前两款 text/JSON 并存。映射规则：finding → result（ruleId、level、message、location.physicalLocation）；level 映射 high→error、medium→warning、low/info→note；file:line 映射为 artifactLocation.uri（相对路径）+ region.startLine。退出码语义不因输出格式改变 | SARIF 便于接入 GitHub Code Scanning 等平台；标准版本固定 2.1.0 |
| A8 | **不给信任分**：只输出逐条 risk signal（finding），无评分、无星级、无"安全/危险"总评——与 eval-harness 无评分红线一致。恶意性判定是 skill-sentry 领域，本款对任何信号不做恶意定性 | 三条红线之一 |
| A9 | CLI 三个子命令（profile / refs / chain）+ 公共 `--format {text,json,sarif}`；每个子命令可独立运行，`audit.py` 不带子命令 → 退出 2（用法错误） | 三块功能输入源不同（快照 JSON / 包目录 / 包目录），拆开职责更清晰 |
| A10 | finding 定位：对包内文件 finding 用 `file:line`；对快照 JSON finding 定位到**键所在行**（快照解析时记录行号），SARIF 中映射为对应 region；对"缺失字段"类 finding 定位到该 JSON 文件 :1 并写明 missing-path | 与 harness 缺失类定位约定（SKILL.md:1）同思路 |
| A11 | CLI 退出码遵循全局规范：0=干净、1=有 finding、2=用法或输入错误（快照 JSON 非法 / schema 不符 / 目录无 SKILL.md / 参数非法）。优先级 2 > 1 > 0 | 组织硬约束 |
| A12 | data-provenance.md 来源：gh api 端点文档 URL（抓取日期 2026-08-30 + 证据强度）、SARIF 2.1.0 OASIS 标准文档 URL、知名 skill 名清单来源（官方 registry / 市场页面存档，抓取日期 + 强度；实现阶段核实后从"未验证"升级）。延续 verified/unverified 快照机制：清单/阈值/端点文档未核实项如实标注 | 不编 URL、不预写未核实来源——诚实文档红线 |

---

## 2. 功能范围

### 2.1 三个子命令与规则编号（S 编号体系）

| 子命令 | 规则 ID | 名称 | 判定逻辑 | finding 强度 |
|--------|---------|------|---------|-------------|
| profile | S1 | stale-repo | 最后提交时点距今（锚点见 A3）超过 stale 阈值 | inferred（附快照值与锚点日期） |
| profile | S2 | single-maintainer | contributors/维护者去重后数量低于最低约定 | inferred |
| profile | S3 | no-recent-release | release 节奏窗口内无发布或从未发布 | inferred |
| profile | S4 | high-open-ratio | open issue 占比超过约定阈值 | inferred |
| profile | S5 | archived-or-fork | archived=true 或 fork=true 标志 | inferred |
| refs | S6 | plaintext-endpoint | 外部 URL 或字面量端点使用明文 http:// | explicit |
| refs | S7 | raw-ip-endpoint | 字符串字面量中出现 IP 直连端点 | explicit |
| chain | S8 | risky-install-pattern | 文档中出现 `curl … \| sh` / `curl … \| bash` 模式 | explicit |
| chain | S9 | package-manager-prompt | 文档中 pip/npm 安装提示指向非官方 registry 域名（对照规则数据内置 registry 白名单） | explicit |
| chain | S10 | name-impersonation | 包名/候选名与知名 skill 名清单相似度过阈值，或命中 typosquat 变体模式 | inferred（附双方名称与相似度度量值） |

反例保护（不触发）：`https://` 正常链接（S6）、文档中作为**反面示例引用**的 curl|sh 字样位于代码块且上下文含 "不要" / "avoid" / "do not" 标注（S8 反例，实现阶段以"代码块内 + 否定词"双条件判定，无法判定时报 unverified 不硬报）、同名完全匹配知名清单（S10 反例：与知名名完全一致不算仿冒——那是"知名 skill 本尊"，只报相似非相同）、gh api 快照 contributors 为空数组但 fetched_at 早于仓库创建日（数据未拉全，报输入警告不报 S2）。

### 2.2 清单输出与 finding 的分离（refs 子命令特有）

refs 子命令输出两部分：
1. **端点清单**（信息性，不计入退出码）：外部 URL 全量列表，每项附来源 file:line 与"清单项，非 finding"标注；
2. **finding**（S6/S7，计入退出码）。

报告头部固定声明："清单 ≠ 风险；端点的安全性不在本 skill 判定范围（运行时行为归 skill-sentry）。"

### 2.3 证据强度模型（对齐前三款）

| 强度 | 定义 |
|------|------|
| explicit | 包内可验证事实（S6–S9：文件中的字面模式） |
| inferred | 由快照 + 阈值约定推导（S1–S5、S10），finding 必须附：快照原始值、锚点日期、阈值及其"默认约定"标注 |
| unverified | 规则数据中未核实来源的清单/阈值/文档引用；快照缺少 fetched_at 时的时间基准 |
| 未验证 | 任何"这个包是否安全/可信"的总评——一律不做断言，无信任分（A8） |

---

## 3. SKILL.md 全文草案（约 210 行，< 500 行门禁内）

````markdown
---
name: skill-supply-chain-audit
description: Builds an origin-side supply-chain profile for any third-party Agent
  Skill package - where it comes from, who maintains it, and how risky its
  distribution path looks. Works fully offline on user-provided snapshots: gh api
  export JSON (repo metadata, commits, contributors, releases), git remote output,
  and marketplace HTML archives. Three deterministic checks - repository health
  signals (staleness, maintainer count, release cadence, issue ratio, archived/fork
  flags), reference surface inventory (external URLs and declared script endpoints,
  listed but not judged), and distribution-chain risks (curl|sh install patterns,
  non-official registry prompts, name-impersonation signals against a built-in
  well-known-skill list). Outputs findings with file:line locations in text, JSON,
  or SARIF 2.1.0 format. Does NOT judge whether code is malicious, does NOT access
  the network, and does NOT produce trust scores - signals only, no ratings. Use
  when reviewing a skill's provenance before adoption, auditing a repository's
  maintenance health from a gh api export, or checking a package name for
  typosquat-style impersonation.
---

# Skill Supply Chain Audit

对第三方 Skill 包做**来源侧**供应链画像：从哪来、谁维护、分发链路风险如何。
确定性脚本离线完成全部检测，只输出逐条 risk signal，无信任分。

## When to use this skill

满足以下任一场景时触发：

1. 用户要在采用某个第三方 skill 前评估其来源与维护状况
2. 用户提供 gh api 导出 JSON，要求分析仓库健康度（最后提交、维护者数、release 节奏）
3. 用户要求列出 skill 包引用的全部外部 URL 与 scripts 声明的端点清单
4. 用户要求检查 skill 的安装文档有没有 curl|sh 类分发风险
5. 用户怀疑某个 skill 名称仿冒知名 skill（typosquat）
6. 用户要求输出 SARIF 格式的供应链审计报告
7. 用户要求分析 git remote / 市场页面存档中的来源信息
8. 用户在 CI 中对候选 skill 做来源侧准入检查

## When NOT to use this skill

以下场景**不**触发本 skill：

1. 用户要求检测 skill 代码是否恶意（注入、后门、窃密）——这是 skill-sentry 的职责，
   本款对任何信号不做恶意定性
2. 用户要求评估 skill 包结构质量（frontmatter、行数、fixtures 契约）——这是
   skill-eval-harness 的职责
3. 用户要求联网抓取仓库最新数据、实时查询 npm/pypi——本款不联网，
   只解析用户提供的快照
4. 用户要求给供应链风险打分或给出"可信/不可信"结论——本款只出逐条
   risk signal，无评分、无总评

## Workflow

1. **收集快照**（用户侧，本 skill 不联网）：

   ```bash
   gh api repos/OWNER/REPO > repo.json
   gh api repos/OWNER/REPO/commits --paginate > commits.json
   gh api repos/OWNER/REPO/contributors > contributors.json
   git remote -v > remote.txt   # 可选
   ```

2. **运行画像**（确定性，全部 finding 由脚本产生）：

   ```bash
   python scripts/audit.py profile repo.json commits.json contributors.json \
       [--format sarif]
   python scripts/audit.py refs <skill-dir>
   python scripts/audit.py chain <skill-dir> [--against remote.txt]
   ```

3. **解读 finding**：逐条报告 `file:line`、规则 ID、快照原始值、锚点日期与阈值标注；
   每条 inferred finding 必须把"快照值 + 阈值约定"的推理链说给用户听。
4. **边界声明**：清单 ≠ 风险；信号 ≠ 恶意；无信任分。快照数据的时效性以
   fetched_at 为准，过期快照结论如实标注。

## Finding format

每条 finding 固定字段：

```
[finding] repo.json:7  rule=S1  strength=inferred
  signal:   last push 2024-11-02, anchor fetched_at=2026-08-30 -> stale
  basis:    threshold 180d is a default convention (see references/rules.md), not a fact
```

## Evidence strength

- **explicit**：包内文件中的字面模式（S6–S9）
- **inferred**：快照值 + 阈值约定推导（S1–S5、S10），附原始值与锚点
- **unverified**：未核实的清单/阈值/文档引用；缺 fetched_at 的时间基准
- **未验证**：包是否安全可信的总评——一律不做断言

## Boundaries and red lines

- 离线运行，绝不发起网络请求；来源数据全部来自用户提供的快照
- 不判定恶意行为（skill-sentry 领域）；不给信任分、无总评（与 eval-harness 红线一致）
- 端点清单只列举不定性；端点安全性不在本 skill 判定范围
- 阈值与相似度门槛是"默认约定"，报告中必须逐条标注，不冒充事实
- 只报告，不修改用户文件
- 不输出任何性能数字（未实测的性能一律不写）
- 退出码：0 = 无 finding；1 = 有 finding；2 = 用法或输入错误
  （快照非法 / 目录无 SKILL.md / 参数非法）

## End-to-end example

```bash
$ python scripts/audit.py chain fixtures/chain-curl-sh/
[finding] fixtures/chain-curl-sh/SKILL.md:14  rule=S8  strength=explicit
  signal:   install prompt "curl -fsSL https://x.example/i.sh | sh"
  basis:    distribution-chain pattern (see references/rules.md)
[finding] fixtures/chain-curl-sh/SKILL.md:1  rule=S10  strength=inferred
  signal:   name "skill-sentryy" vs well-known "skill-sentry" (edit distance 1)
  basis:    impersonation threshold is a default convention, not a fact
2 findings. exit code: 1
```
````

---

## 4. agents/openai.yaml 草案

```yaml
# 跨客户端兼容描述。触发场景集合必须与 SKILL.md description 等价（措辞可不同）。
name: skill-supply-chain-audit
version: 0.1.0
description: >
  Origin-side supply-chain profiler for third-party Agent Skill packages, fully
  offline on user-provided snapshots (gh api export JSON, git remote output,
  marketplace HTML archives). Repository health signals: last-push staleness
  against the snapshot's fetched_at anchor, maintainer/contributor count, release
  cadence, open-issue ratio, archived/fork flags. Reference surface: inventory of
  external URLs and declared script endpoints (listed, not judged), with findings
  for plaintext http:// endpoints and raw-IP endpoints. Distribution chain:
  curl|sh install patterns, non-official registry prompts, and name-impersonation
  signals against a built-in well-known-skill list. Findings carry file:line
  locations; output formats are text, JSON, and SARIF 2.1.0. Signals only - does
  NOT judge maliciousness (skill-sentry's scope), does NOT assess package structure
  quality (skill-eval-harness's scope), and does NOT produce trust scores.
when_to_use:
  - Review a third-party skill's provenance and maintenance health before adoption
  - Analyze repository health from a gh api export snapshot
  - Inventory external URLs and declared endpoints in a skill package
  - Check install docs for curl|sh or non-official registry distribution risks
  - Detect typosquat-style name impersonation against well-known skills
  - Produce a SARIF 2.1.0 supply-chain audit report in CI
when_not_to_use:
  - Detecting malicious code behavior (use skill-sentry)
  - Evaluating package structure quality (use skill-eval-harness)
  - Fetching live repository or registry data (offline, snapshots only)
  - Producing a trust score or safe/unsafe verdict (signals only)
cli:
  entry: scripts/audit.py
  runtime: python3
  subcommands: [profile, refs, chain]
  formats: [text, json, sarif]
  exit_codes:
    0: no findings
    1: findings present (risk signals)
    2: usage or input error
```

---

## 5. scripts/ 模块清单（纯标准库）

### 5.1 模块划分

| 模块 | 职责 | 关键函数签名（草案） |
|------|------|---------------------|
| `audit.py` | CLI 入口 + 编排，三个子命令 profile/refs/chain，公共 `--format` | `main(argv: list[str]) -> int`<br>`cmd_profile(args) -> int` / `cmd_refs(args) -> int` / `cmd_chain(args) -> int` |
| `snapshot.py` | 快照解析：gh api 导出 JSON（**逐键记录行号**，支撑 A10）、remote.txt、市场页面 HTML 存档的最小文本提取；schema 校验（缺 fetched_at 等输入警告） | `load_gh_export(paths: dict[str, str]) -> Snapshot`<br>`@dataclass Snapshot: repo, commits, contributors, releases, fetched_at, key_lines: dict[str, tuple[str, int]]` |
| `chain_rules.py` | 纯数据模块（复用 directory_data.py 模式）：知名 skill 名清单、风险模式（curl\|sh 等 regex）、registry 白名单、默认阈值表（stale 天数/最低维护者数/相似度门槛，逐项带 `default_convention: true` 标志）、SARIF level 映射表、规范依据引用键 | `WELL_KNOWN_SKILLS: frozenset[str]`<br>`RISK_PATTERNS: list[Pattern]`<br>`THRESHOLDS: dict[str, Threshold]`<br>`@dataclass Threshold: value, unit, is_convention` |
| `checkers.py` | S1–S10 实现：profile 组（S1–S5，快照+阈值）、refs 组（S6–S7 + 端点清单输出）、chain 组（S8–S10） | `run_profile(snap: Snapshot) -> list[Finding]`<br>`run_refs(skill_dir: str) -> tuple[list[Finding], Inventory]`<br>`run_chain(skill_dir: str, remote: str \| None) -> list[Finding]`<br>`name_similarity(a: str, b: str) -> int`（编辑距离） |
| `report.py` | text/JSON 双格式渲染 | `render_text(findings: list[Finding], inventory: Inventory \| None) -> str`<br>`render_json(findings: list[Finding], inventory: Inventory \| None) -> dict` |
| `sarif.py` | SARIF 2.1.0 渲染：result/rule 映射、level 映射（high→error / medium→warning / low,info→note）、file:line → artifactLocation.uri + region.startLine、`$schema` 与 version=2.1.0 固定 | `render_sarif(findings: list[Finding], tool_name: str) -> dict` |

依赖方向：`audit.py → {snapshot, checkers, report, sarif} → chain_rules`。禁止反向依赖。

### 5.2 CLI 参数设计

```
usage: python audit.py <subcommand> ...

profile REPO_JSON COMMITS_JSON CONTRIBUTORS_JSON [--releases RELEASES_JSON]
        [--format {text,json,sarif}] [--output FILE] [--quiet]
  gh api 快照集；releases 可选；锚点优先快照 fetched_at
refs SKILL_DIR [--format ...] [--output FILE] [--quiet]
  引用面：端点清单（信息性）+ S6/S7 finding
chain SKILL_DIR [--against REMOTE_TXT] [--format ...] [--quiet]
  分发链：S8–S10；--against 提供来源对照（可选）
```

通用约定：

- 三个子命令共用 `--format`；SARIF 模式下端点清单不进 SARIF（SARIF 只装 finding）；
- profile 快照缺 fetched_at → 报告标注"以本机日期为基准，未验证"，不视为输入错误；
- 快照 JSON 非法 / 结构不符 schema / 目录无 SKILL.md / 不带子命令 → 退出 2；
- 无 finding 时输出 `0 findings`，退出 0。

### 5.3 退出码语义表

| 退出码 | 语义 | 触发条件 |
|--------|------|---------|
| 0 | 干净/通过 | 无任何 finding（端点清单存在不影响） |
| 1 | 有 finding | S1–S10 至少一条 |
| 2 | 用法或输入错误 | 快照非法/schema 不符/无 SKILL.md/参数非法/缺子命令。优先级 2 > 1 > 0 |

---

## 6. references/ 文档清单

| 文件 | 内容 |
|------|------|
| `data-provenance.md` | 来源逐项附 URL + 抓取日期 2026-08-30 + 证据强度：gh api 端点文档（repo/commits/contributors/releases）、SARIF 2.1.0 OASIS 标准文档、知名 skill 名清单（官方 registry / 市场页面存档，实现阶段核实后从"未验证"升级）、registry 白名单来源。延续 verified/unverified 快照机制；全文显著声明"快照会过期，结论以抓取时点为准" |
| `rules.md` | S1–S10 逐条判定逻辑、阈值表及其"默认约定"性质声明、反例保护清单（§2.1，含否定语境双条件判定口径）、清单 vs finding 的分离规则 |
| `evidence-model.md` | 证据强度定义、时间锚点规则（fetched_at 优先 / 本机日期标注未验证）、无信任分原则、SARIF level 映射依据 |
| `scope.md` | **四条边界**：①skill-sentry（恶意行为判定，本款对信号不定性）；②skill-eval-harness（包内结构质量，本款只管来源与分发）；③geo-evidence-audit（地理声称，互不重叠）；④ai-tool-directory-publisher（listing 材料与一致性，互不重叠） |

不创建 README / CHANGELOG / 安装指南（硬约束：进根 README）。

---

## 7. fixtures/ 清单（15 项，全部用 Write 工具逐个写）

快照类夹具为最小化 gh api 导出 JSON（结构对齐 snapshot.py schema，内容为构造数据，逐键换行以支撑行号定位断言）。

| # | 夹具 | 场景 | 预期退出码 | 预期 finding 数 |
|---|------|------|-----------|----------------|
| 1 | `healthy-repo.json` + commits/contributors | 活跃仓库：近期提交、多维护者、有 release | 0 | 0 |
| 2 | `stale-repo.json` 等 | 最后提交距 fetched_at 超阈值 + 单维护者 | 1 | 2（S1 + S2） |
| 3 | `archived-repo.json` | archived=true | 1 | 1（S5） |
| 4 | `no-release-repo.json` | 从未发布 release | 1 | 1（S3） |
| 5 | `refs-clean/` | 迷你 skill 包，仅内部引用 | 0 | 0 |
| 6 | `refs-external/` | SKILL.md 含明文 http:// URL | 1 | 1（S6；端点清单同时输出） |
| 7 | `endpoints-raw-ip/` | scripts 字面量含 IP 直连端点 | 1 | 1（S7） |
| 8 | `chain-curl-sh/` | 安装文档含 `curl … \| sh` + 名称仿冒（skill-sentryy） | 1 | 2（S8 + S10） |
| 9 | `npm-official-prompt/` | 文档 pip/npm 提示指向官方 registry | 0 | 0（S9 反例保护） |
| 10 | `npm-unofficial-prompt/` | 安装提示指向非官方 registry 域名 | 1 | 1（S9） |
| 11 | `same-name-known/` | 名称与知名清单完全一致 | 0 | 0（S10 反例保护） |
| 12 | `malformed-export.json` | 非法 JSON | 2 | —（输入错误） |
| 13 | `schema-missing-export.json` | 合法 JSON 但缺必需键 | 2 | —（输入错误） |
| 14 | `no-fetched-at-export.json` | 缺 fetched_at（可运行，锚点降级） | 1 | 1（S1，报告标"未验证"锚点） |
| 15 | `e2e-pack/`（目录） | 迷你包 + 全套快照：含 S1 + S6 + S8 各一处 | 1 | 3 |

SARIF 校验夹具（并入 #1、#2 的运行断言，不单列目录）：对 #2 跑 `--format sarif`，断言 `$schema` 与 `version=2.1.0`、result 数 = finding 数、level 映射正确（S1=inferred/medium → warning）、`repo.json:行号` 映射进 region.startLine。

> 注：预期退出码与 finding 数是设计目标，实现阶段以实际运行为准校准，偏离需在 PR 说明。全部快照 JSON 与迷你包文件用 Write 工具逐个写。

---

## 8. 测试矩阵（8 触发 + 4 非触发 + 1 端到端）

### 8.1 触发测试（T1–T8）

| ID | 用户输入（示意） | 预期行为 |
|----|----------------|---------|
| T1 | "给这个第三方 skill 做来源侧供应链画像" | 触发；引导收集快照 + 三个子命令按需运行 |
| T2 | "分析这份 gh api 导出，仓库维护还活跃吗" | 触发；profile（S1–S5） |
| T3 | "列出这个 skill 包引用的所有外部 URL 和端点" | 触发；refs 清单 + S6/S7 |
| T4 | "检查这个 skill 的安装文档有没有 curl\|sh 风险" | 触发；chain（S8） |
| T5 | "这个名字是不是仿冒知名 skill" | 触发；chain（S10），报告附相似度与阈值标注 |
| T6 | "输出 SARIF 格式的供应链审计报告" | 触发；--format sarif |
| T7 | "这个仓库是不是很久没维护了" | 触发；profile（S1），附锚点与阈值说明 |
| T8 | "对候选 skill 做来源侧准入检查（CI 场景）" | 触发；profile + chain 组合，退出码门禁 |

### 8.2 非触发测试（N1–N4）

| ID | 用户输入（示意） | 预期行为 |
|----|----------------|---------|
| N1 | "扫描这个 skill 有没有恶意代码和后门" | 不触发（skill-sentry 职责） |
| N2 | "评估这个 skill 包的结构质量是否合规" | 不触发（skill-eval-harness 职责） |
| N3 | "联网抓一下这个仓库的最新 stars 和 issues" | 不触发（不联网红线，如实拒绝并引导用户自行导出快照） |
| N4 | "给这个 skill 的供应链安全打个分" | 不触发（无信任分红线，如实拒绝） |

### 8.3 端到端测试（E1）

对 `fixtures/e2e-pack/` 完整走一遍：profile 断言退出 1 且 S1 finding 含快照原始值 + 锚点日期 + 阈值标注；refs 断言端点清单输出且 S6 计入退出码；chain 断言 S8 finding 含 file:line；text/JSON/SARIF 三种格式均可解析且 finding 数一致（SARIF 不含清单项）；退出码三格式一致。

### 8.4 脚本级单元测试（CI 矩阵执行）

- fixtures #1–#14 全量跑：预期退出码逐一断言（预期 exit 1 的用例一律 `if` 包裹）；
- SARIF 断言：#2 的 `$schema`/version/result 数/level 映射/region 行号；
- `--against remote.txt`：对 #8 附来源对照后断言 S10 推理链输出；
- 反例保护：#9、#11、否定语境 curl|sh 夹具、contributors 空数组+未拉全夹具 断言 0 finding / 仅输入警告；
- 退出码 2：#12、#13、不存在路径、缺子命令；
- 锚点降级：#14 断言"未验证"标注出现在报告。

### 8.5 CI 写法强制约定

```bash
# 预期 exit 1 的唯一允许写法（if 包裹 + 成功则显式失败）
if python skills/skill-supply-chain-audit/scripts/audit.py profile \
    skills/skill-supply-chain-audit/fixtures/stale-repo.json \
    skills/skill-supply-chain-audit/fixtures/stale-commits.json \
    skills/skill-supply-chain-audit/fixtures/stale-contributors.json > /dev/null; then
  echo "::error::expected exit 1, got 0"; exit 1
fi
# 注意：不允许 `|| true`（会把 exit 2 也吞成"通过"）
```

自举（A 系列既有约定延续）：设计完成后用 eval-harness novera 档评估本款包（`python skills/skill-eval-harness/scripts/audit.py skills/skill-supply-chain-audit/`），预期 0 finding——本 SKILL.md 按 8+4+1 结构、frontmatter 仅 name+description、无 README、fixtures 按 MANIFEST 约定编写。此断言进本款 CI 步骤。

---

## 9. 硬约束核对清单（本 skill 设计 × 全局 10 条）

| 约束 | 落位 |
|------|------|
| 纯标准库零依赖，3.9+ | §5.1 全部标准库；编辑距离/regex/AST 均标准库实现；CI py39 门禁 |
| 退出码 0/1/2 | §5.3 |
| finding 带 file:line | §2.1/§3 Finding format；快照 JSON 键行号定位（A10）；SARIF region 映射（A7） |
| 性能数字不预写 | 全文无性能声明；SKILL.md 红线显式禁止 |
| 外部事实 URL + 日期 + 证据强度 | §6 data-provenance.md（gh api / SARIF / 知名清单逐项附 URL + 2026-08-30 + 强度） |
| 目录结构四件套 | SKILL.md + agents/openai.yaml + scripts/ + references/ + fixtures/ |
| SKILL.md < 500 行 | §3 约 210 行，CI wc -l 门禁 |
| 确定性脚本优先 | §3 Workflow 第 2 步"全部 finding 由脚本产生" |
| 诚实文档红线 | A4/A6 阈值为"默认约定"逐条标注；A8 无信任分；§2.3 未验证档位；§7 预期数以实际运行为准 |
| 预期 exit 1 用 if 包裹 | §8.5 |
| 夹具用 Write 工具逐个写 | §7 标注（实现阶段执行） |
| 目录数据纯数据模块 | §5.1 chain_rules.py（复用 directory_data.py 模式） |

---

## 10. 待用户确认项汇总

1. §1 解读假设 A1–A12 逐条核对（尤其是 A3 时间锚点取 fetched_at 优先、A5 清单不计入退出码、A8 无信任分红线）；
2. A4 默认阈值草案值（stale 天数、最低维护者数、open issue 比例、相似度门槛）实现阶段与用户逐项确认；
3. A2 快照输入范围：v0.1 是否纳入市场页面 HTML 存档解析（当前设计：纳入但仅最小文本提取），或先只支持 gh api JSON + remote.txt；
4. §7 夹具"预期 finding 数"是否认可作为验收基线。

确认后进入实现阶段（排期由 team-lead 决定）。
