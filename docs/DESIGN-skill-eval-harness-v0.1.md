# skill-eval-harness v0.1.0 完整设计

> 设计人：软件架构师（高见远）
> 状态：设计稿，待用户核对 §1「解读假设」后定稿
> 所属：novera-skills mono-repo 第 3 款 skill（`skills/skill-eval-harness/`）
> 前序：geo-evidence-audit v0.1.0、ai-tool-directory-publisher v0.1.0 已发布；本设计复用两者沉淀的骨架惯例（纯数据模块、verified/unverified 快照、if 包裹）
> 本文档是设计，不含实现代码；文中代码块均为草案签名与格式约定。

---

## 1. 解读假设（供用户逐条核对纠偏）

原始提示词全文丢失，以下为本设计对名称 "skill-eval-harness"（Skill 评估台）的语义重构。**每条都可能被用户推翻，推翻后按 §10 修订流程更新设计。**

| # | 假设 | 依据与范围取舍 |
|---|------|---------------|
| A1 | 核心定位：对**任意第三方 Agent Skill 包**（SKILL.md + scripts/ + references/ + fixtures/ 的目录）做结构化质量评估，输出逐条可判定的 finding 与汇总。用户两类：skill 作者发布前自查、使用者安装前检查 | 任务建议方向"评估基准/评测台"；harness 一词强调可重复运行的判定装置 |
| A2 | **与本仓库自身 CI 的分工**：`tools/py39_gate.py` 与 `skills-ci.yml` 管的是 novera-skills 仓库自己的门禁；skill-eval-harness 是独立 skill 产品，装进用户环境后评估任意 skill 目录。两者共享检查**思想**，不共享运行时代码，互不调用 | 任务背景显式要求；边界写入 references/scope.md |
| A3 | **与 skill-sentry 的分工**：sentry 管**恶意行为**（安全审计：窃密、后门、破坏性操作）；eval-harness 管**结构与质量合规**。eval-harness 对"脚本是否有恶意"不做任何判断——哪怕它评估的包里出现网络调用，也只报"违反结构规范"，不定性为恶意 | 三条分工边界之一；恶意定性需要行为分析，超出结构评估范围 |
| A4 | **与 skill-supply-chain-audit 的分工**：supply-chain 管**来源侧画像**（出处、依赖来源、维护者）；eval-harness 管**包内现状**（目录里实际有什么、合不合规）。本 skill 评估全程**不联网**，不追溯任何包的来源 | 三条分工边界之一；A3/A4 与本仓库 CI 边界共同构成 scope.md 三节 |
| A5 | 检查项四组（见 §2.1）：SKILL.md 合规、scripts 质量门禁、fixtures 契约、结构完整性。全部为**可判定**检查（存在性/计数/枚举/AST 事实），不做主观评分、百分制、星级——诚实红线：判不了的就不出检查项 | 任务背景"只做可判定的检查项" |
| A6 | 触发/非触发/端到端清单校验提供**两档 profile**：`minimal`（只查三节存在性，不查数量）与 `novera`（查存在性且计数 8+4+1）。默认 novera。理由：8+4+1 是本组织规范，第三方 skill 未必遵守，minimal 档保证产品对任意包可用 | 组织前缀规范 vs 通用产品定位的调和 |
| A7 | scripts 检查用 **AST 事实**而非文本 grep：import 检查对照内置标准库清单（Python 3.9 无 `sys.stdlib_module_names`，清单内置在纯数据模块）；网络/spawn 禁用检查走 AST 节点匹配（socket/urllib.request/http.client/subprocess/os.system 等）。文本 grep 误报率高（注释/字符串会误中） | 零依赖 + 3.9 约束下的确定性方案 |
| A8 | fixtures 契约校验：检查夹具文件存在性、SKILL.md 中声明的预期退出码可被识别（约定：夹具文件名或清单文件标注，如 `fixtures/MANIFEST` 或文件名内嵌 `exit1` 后缀——默认接受两种约定，实现阶段定稿一种）。**不实际运行**被评估 skill 的脚本（运行第三方代码超出生包静态评估边界，运行时安全归 sentry） | 静态评估边界；执行第三方脚本是安全敏感操作，v0.1 不做，SKILL.md 红线声明 |
| A9 | 输入为**单个 skill 目录**（必须含 SKILL.md，否则退出 2）。一次评估一个包；多包评估由用户循环调用或 CI 矩阵承担，harness 自身不做多包聚合 | 单一职责；多包聚合属于 CI/上层编排职责 |
| A10 | finding 定位：文件级问题定位到 `file:line`（SKILL.md 内问题定位到具体行）；**缺失类**问题（文件/目录不存在）定位到 `SKILL.md:1` 或包根并在 finding 里写明"missing" | 缺失物没有行号可指，需要确定性约定 |
| A11 | CLI 退出码遵循全局规范：0=干净（全部检查项通过）、1=有 finding、2=用法或输入错误（目录不存在/无 SKILL.md/参数非法）。优先级 2 > 1 > 0 | 组织硬约束 |
| A12 | 评测标准的规范来源（Agent Skills 开放标准要点、本组织《通用前缀规范》）内置为**规则数据**（纯数据模块，复用 directory_data.py 模式）；标准文档的引用 URL 在实现阶段核实后填入 data-provenance.md，未核实前标"未验证"（延续第 2 款 verified/unverified 快照机制） | 不编 URL、不预写未核实的规范条文——诚实文档红线 |

---

## 2. 功能范围

### 2.1 检查项四组（E 编号体系）

| 组 | ID | 名称 | 判定逻辑 | profile |
|----|----|------|---------|---------|
| SKILL.md | E1 | frontmatter-fields | frontmatter 必须存在且仅含 name、description 两字段（多字段/缺字段均报） | both |
| SKILL.md | E2 | line-budget | SKILL.md 全文行数 < 500 | both |
| SKILL.md | E3 | trigger-inventory | 存在触发场景清单（novera 档另查：触发 8、非触发 4、端到端 1，计数精确匹配） | minimal 查存在性 |
| SKILL.md | E4 | exit-code-declared | SKILL.md 声明 0/1/2 退出码语义 | both |
| scripts | E5 | stdlib-only | scripts/*.py 的 import 全部落在内置标准库清单内（AST Import/ImportFrom 节点） | both |
| scripts | E6 | no-network-spawn | AST 检出网络/进程派生调用（socket、urllib.request、http.client、subprocess、os.system/popen/exec*/spawn*）即报 | both |
| scripts | E7 | syntax-parse | 每个 .py 通过 `ast.parse(feature_version=(3,9))` 语法门禁 | both |
| scripts | E8 | finding-lineage | SKILL.md 或 scripts 内存在"finding 带 file:line"的自检依据（声明文本或代码中的 line 字段） | novera |
| fixtures | E9 | fixtures-contract | SKILL.md 引用的夹具文件存在；夹具与预期退出码声明的对应关系可识别（按 A8 约定） | both |
| structure | E10 | openai-yaml | agents/openai.yaml 存在，且 name 字段与 SKILL.md frontmatter name 一致 | both |
| structure | E11 | references-nonempty | references/ 目录存在且非空 | both |
| structure | E12 | no-forbidden-files | 目录内无 README*、CHANGELOG*、安装指南类文件 | both |

反例保护（不触发）：scripts 中出现在**注释或字符串字面量**里的 `import socket` 字样（AST 只看真实 import 节点）、标准库内部子模块导入（如 `argparse.sub` 不存在但 `urllib.parse`——清单按顶级模块判定，`urllib.parse` 属 stdlib 顶级 `urllib`，不误报）、SKILL.md 行数 499（边界内通过）、目录名含 README 字样的非 README 文件（按精确文件名模式 `README*` 判定）。

### 2.2 证据强度模型（对齐前两款）

| 强度 | 定义 |
|------|------|
| explicit | 直接对照包内事实得出（E1–E12 全部为 explicit：存在性/计数/AST 均为包内可验证事实） |
| inferred | 无（v0.1 无跨文件推导类检查，保留档位以对齐统一模型） |
| unverified | 规则数据中尚未核实规范来源的检查项（如 novera 档的 8+4+1 计数依据《通用前缀规范》，实现阶段核实标准原文后升级）——此类检查项默认仍运行，但报告标注其规范依据状态 |
| 未验证 | 任何"这个 skill 质量好不好/能不能被客户端采纳"的综合评价——harness 只输出逐条 finding，不做总评断言 |

### 2.3 报告结构

```
skill-eval-harness report: <skill-dir>
  profile: novera        checks: 12 run / 0 skipped
  [finding] <file:line>  rule=E5  strength=explicit
    issue:   import "requests" not in stdlib allowlist
    basis:   novera profile E5 (see references/rules.md)
  summary: 1 finding across 12 checks. exit code: 1
```

不做总分、不做 pass/fail 单一结论字段（finding 数本身就是判定依据；JSON 报告含逐条 finding 与 checks_run/checks_skipped 计数）。

---

## 3. SKILL.md 全文草案（约 200 行，< 500 行门禁内）

````markdown
---
name: skill-eval-harness
description: Evaluates any Agent Skill package (SKILL.md + scripts/ + references/ +
  fixtures/) against a deterministic, checkable quality baseline and emits per-finding
  reports with file:line locations. Checks SKILL.md frontmatter discipline (only
  name and description), line budget, trigger/non-trigger/end-to-end inventory
  counts, exit-code semantics declaration, scripts for third-party imports and
  network/spawn calls via AST analysis, fixtures contract presence, and structural
  integrity (agents/openai.yaml consistency, non-empty references/, no stray
  README/CHANGELOG). Fully offline, standard library only, pass/fail per check -
  no subjective scoring. Use when a skill author wants a pre-release self-check, a
  user wants to inspect a skill before installing it, or CI needs a repeatable
  skill-package evaluation. Does NOT detect malicious behavior, does NOT analyze
  provenance or maintainers, and does NOT execute the evaluated skill's scripts.
---

# Skill Eval Harness

对 Agent Skill 包做结构化质量评估。确定性脚本离线完成全部检查，只输出可判定
finding，不做主观评分。

## When to use this skill

满足以下任一场景时触发：

1. 用户要发布一个 skill，发布前自查结构是否合规
2. 用户安装某个第三方 skill 前，想先检查它的包结构质量
3. 用户要求检查 SKILL.md 的 frontmatter 是否只含 name/description、行数是否超标
4. 用户要求检查 skill 的 scripts 是否引入第三方依赖或存在网络/进程派生调用
5. 用户要求核对触发/非触发/端到端清单的存在性与数量（8+4+1）
6. 用户要求核对 fixtures 契约：夹具齐全、预期退出码可识别
7. 用户要求检查 agents/openai.yaml 存在且与 SKILL.md 一致、references/ 非空、
   无 README/CHANGELOG 混入
8. 用户在 CI 中需要对 skill 包做可重复的评估并输出 JSON 报告

## When NOT to use this skill

以下场景**不**触发本 skill：

1. 用户要求检测 skill 是否有恶意行为、后门、窃密逻辑——这是 skill-sentry 的职责，
   eval-harness 只判结构与质量合规，不对行为定性
2. 用户要求分析 skill 的来源、依赖出处、维护者画像——这是
   skill-supply-chain-audit 的职责
3. 用户要求为 skill 仓库搭建 CI workflow 或修改 py39 门禁——那是仓库工程任务，
   不是对包的评估
4. 用户要求给 skill 打分、排名、评星级——本 skill 只做可判定检查项，
   不输出任何主观评分

## Workflow

1. **定位包**：确认待评估 skill 目录（必须含 SKILL.md）。
2. **运行评估**（确定性，全部 finding 由脚本产生）：

   ```bash
   python scripts/audit.py <skill-dir>                   # 默认 novera 档
   python scripts/audit.py <skill-dir> --profile minimal # 只查存在性
   python scripts/audit.py <skill-dir> --format json     # JSON 报告
   ```

3. **解读 finding**：逐条报告 `file:line`、规则 ID、问题与依据；缺失类 finding
   按约定定位到 SKILL.md:1 或包根并写明 missing。
4. **修复建议**：可建议修复方向，但脚本不改用户文件；修复后重跑形成闭环。
5. **边界声明**：评估是静态的——不运行被评估 skill 的脚本、不判定恶意性、
   不做质量总评。

## Finding format

每条 finding 固定字段：

```
[finding] skills/<pkg>/SKILL.md:12  rule=E1  strength=explicit
  issue:   frontmatter contains extra field "license"
  basis:   novera profile E1 (see references/rules.md)
```

## Evidence strength

- **explicit**：包内可验证事实（存在性/计数/AST），全部 E1–E12 属此类
- **unverified**：规范依据尚未核实的检查项，报告如实标注
- **未验证**：对 skill 整体质量的综合判断——一律不做断言

## Boundaries and red lines

- 离线运行，绝不发起网络请求
- 不执行被评估 skill 的任何脚本（静态评估；运行时行为归 skill-sentry 领域）
- 不判定恶意行为（skill-sentry）、不分析来源与维护者（skill-supply-chain-audit）、
  不接管仓库自身 CI（tools/py39_gate.py 与 skills-ci.yml）
- 只做可判定检查项：无评分、无星级、无排名、无总评
- 只报告，不修改用户文件
- 不输出任何性能数字（未实测的性能一律不写）
- 退出码：0 = 全部检查项通过；1 = 有 finding；2 = 用法或输入错误
  （目录不存在 / 无 SKILL.md / 参数非法）

## End-to-end example

```bash
$ python scripts/audit.py fixtures/e2e-demo/
skill-eval-harness report: fixtures/e2e-demo/
  profile: novera        checks: 12 run / 0 skipped
  [finding] fixtures/e2e-demo/scripts/helper.py:3  rule=E5  strength=explicit
    issue:   import "requests" not in stdlib allowlist
    basis:   novera profile E5 (see references/rules.md)
  summary: 1 finding across 12 checks. exit code: 1
```
````

---

## 4. agents/openai.yaml 草案

```yaml
# 跨客户端兼容描述。触发场景集合必须与 SKILL.md description 等价（措辞可不同）。
name: skill-eval-harness
version: 0.1.0
description: >
  Deterministic, offline evaluator for Agent Skill packages. Assesses any skill
  directory (SKILL.md + scripts/ + references/ + fixtures/) against a checkable
  baseline: SKILL.md frontmatter discipline (only name and description), line
  budget, trigger/non-trigger/end-to-end inventory (existence, or exact 8+4+1
  counts under the novera profile), exit-code semantics declaration, scripts
  free of third-party imports and network/spawn calls via AST analysis, fixtures
  contract presence, and structural integrity (agents/openai.yaml consistency,
  non-empty references/, no stray README/CHANGELOG). Emits per-finding reports
  with file:line locations in text or JSON. Pass/fail per check only - no
  subjective scoring. Does NOT execute the evaluated skill's scripts, does NOT
  detect malicious behavior (that is skill-sentry's scope), and does NOT analyze
  provenance (that is skill-supply-chain-audit's scope).
when_to_use:
  - Pre-release self-check for a skill author
  - Inspect a third-party skill package before installing it
  - Verify SKILL.md compliance (frontmatter fields, line budget, trigger inventory)
  - Check skill scripts for third-party imports or network/spawn calls
  - Repeatable skill-package evaluation in CI with JSON reports
when_not_to_use:
  - Detecting malicious behavior or backdoors (use skill-sentry)
  - Analyzing provenance, dependencies origin, or maintainers (use skill-supply-chain-audit)
  - Building or modifying repository CI workflows
  - Scoring, ranking, or rating skills (pass/fail findings only)
cli:
  entry: scripts/audit.py
  runtime: python3
  exit_codes:
    0: all checks passed
    1: findings present
    2: usage or input error (missing dir, no SKILL.md, bad args)
```

---

## 5. scripts/ 模块清单（纯标准库）

### 5.1 模块划分

| 模块 | 职责 | 关键函数签名（草案） |
|------|------|---------------------|
| `audit.py` | CLI 入口 + 编排：定位包 → 加载 profile → 逐检查项运行 → 汇总退出码 | `main(argv: list[str]) -> int`<br>`eval_skill(skill_dir: str, profile: str) -> list[Finding]` |
| `skparse.py` | SKILL.md 解析：frontmatter 键值（含行号）、全文行数、触发/非触发/端到端各节的定位与计数 | `parse_skill_md(text: str, path: str) -> SkillDoc`<br>`@dataclass SkillDoc: path, frontmatter: list[Field], total_lines, triggers, non_triggers, e2e, exit_code_declared` |
| `eval_rules.py` | 纯数据模块（复用 directory_data.py 模式）：检查项定义表（E1–E12 × profile 矩阵）、内置标准库模块清单（3.9 兼容，A7 依据）、网络/spawn 禁用名单（模块名 + AST 调用模式）、每项的规范依据引用键 | `CHECKS: dict[str, CheckSpec]`<br>`STDLIB_MODULES: frozenset[str]`<br>`BANNED_CALLS: list[CallPattern]`<br>`@dataclass CheckSpec: id, group, profiles, basis_ref` |
| `checkers.py` | E1–E12 实现：frontmatter 校验、行数、AST 遍历（import/调用节点）、夹具契约、结构完整性 | `run_checks(doc: SkillDoc, skill_dir: str, profile: str) -> list[Finding]`<br>`check_imports(tree: ast.AST, path: str) -> list[Finding]`<br>`check_banned_calls(tree: ast.AST, path: str) -> list[Finding]` |
| `report.py` | 文本/JSON 双格式渲染，含 checks_run/checks_skipped 计数，finding 排序（文件、行号） | `render_text(findings: list[Finding], stats: Stats) -> str`<br>`render_json(findings: list[Finding], stats: Stats) -> dict`<br>`@dataclass Finding: file, line, rule, strength, issue, basis` |

依赖方向：`audit.py → {skparse, checkers, report} → eval_rules`。禁止反向依赖。

### 5.2 CLI 参数设计

```
usage: python audit.py SKILL_DIR [--profile {minimal,novera}] [--only E1,E2,...]
                                 [--format {text,json}] [--output FILE] [--quiet]

SKILL_DIR          待评估的 skill 目录（必须含 SKILL.md）
--profile          评估档位，默认 novera（8+4+1 计数）；minimal 只查存在性
--only             只跑指定检查项，默认全部
--format           报告格式，默认 text
--output           写入文件（缺省打 stdout）
--quiet            只输出 finding 摘要行与退出码
```

行为约定：

- 全部检查项通过 → 输出 `0 findings across N checks`，退出 0；
- 目录不存在 / 无 SKILL.md / 参数不合法 → 退出 2；
- `--only` 引用不存在的检查 ID → 退出 2。

### 5.3 退出码语义表

| 退出码 | 语义 | 触发条件 |
|--------|------|---------|
| 0 | 干净/通过 | 全部运行检查项通过 |
| 1 | 有 finding | E1–E12 至少一条未过 |
| 2 | 用法或输入错误 | 参数不合法、目录不存在、无 SKILL.md。优先级 2 > 1 > 0 |

---

## 6. references/ 文档清单

| 文件 | 内容 |
|------|------|
| `data-provenance.md` | 评测标准来源：Agent Skills 开放标准文档（实现阶段核实官方 URL 后填入，未核实前标"未验证"）、本组织《通用前缀规范》（内部规范，标注为组织内约定）。延续 verified/unverified 快照机制；8+4+1 计数依据、500 行上限依据逐条标注来源与强度 |
| `rules.md` | E1–E12 逐条判定逻辑、profile 矩阵（minimal/novera 差异）、反例保护清单（§2.1）、AST 检查的实现口径（只看真实 import/Call 节点，忽略注释与字符串） |
| `evidence-model.md` | 证据强度定义、静态评估边界（不运行第三方脚本）、"无总评"原则的说明 |
| `scope.md` | **三条分工边界**：①本仓库 CI（tools/py39_gate.py + skills-ci.yml 管自家门禁，harness 是评估任意第三方包的独立产品，不共享运行时）；②skill-sentry（管恶意行为，harness 对行为不定性）；③skill-supply-chain-audit（管来源侧画像，harness 只看包内现状、不联网追溯） |

不创建 README / CHANGELOG / 安装指南（硬约束：进根 README）。

---

## 7. fixtures/ 清单（15 项，全部用 Write 工具逐个写）

夹具为**迷你 skill 包**（每个是一个目录，内含最小化 SKILL.md 与必要文件；夹具内容仅用于触发检查项，不代表真实 skill 语义）。

| # | 夹具 | 场景 | 预期退出码 | 预期 finding 数 |
|---|------|------|-----------|----------------|
| 1 | `good-skill/` | 全合规迷你包（no vera 档全过） | 0 | 0 |
| 2 | `minimal-ok/` | 仅 3 个触发词，无 8+4+1 结构：minimal 档过，novera 档挂 | 0（minimal）/ 1（novera） | 1（E3，novera） |
| 3 | `bad-frontmatter/` | frontmatter 多出 license 字段 | 1 | 1（E1） |
| 4 | `too-long-skillmd/` | SKILL.md 超过 500 行（程序生成填充行） | 1 | 1（E2） |
| 5 | `missing-triggers/` | 无非触发清单节 | 1 | 1（E3） |
| 6 | `third-party-import/` | scripts/helper.py `import requests` | 1 | 1（E5） |
| 7 | `network-call/` | scripts/fetcher.py `import urllib.request` 并调用 | 1 | 2（E5 + E6） |
| 8 | `no-openai-yaml/` | 缺 agents/openai.yaml | 1 | 1（E10） |
| 9 | `readme-in-skill/` | 包内混入 README.md | 1 | 1（E12） |
| 10 | `empty-references/` | references/ 目录为空 | 1 | 1（E11） |
| 11 | `no-exit-code-doc/` | SKILL.md 无退出码语义声明 | 1 | 1（E4） |
| 12 | `broken-syntax/` | scripts/broken.py 语法错误（3.9 门禁内） | 1 | 1（E7） |
| 13 | `fixtures-missing/` | SKILL.md 引用的夹具文件不存在 | 1 | 1（E9） |
| 14 | `not-a-skill/` | 目录内无 SKILL.md | 2 | —（输入错误） |
| 15 | `e2e-demo/` | 端到端夹具：内含 1 处 E5 违规的迷你包 | 1 | 1 |

边界夹具补充（并入 #1 或 #15 内）：`comment-mention/`（注释里出现 `import socket` 字样——E5 反例保护，0 finding）、`line-499/`（SKILL.md 恰 499 行——E2 反例保护，0 finding）、`urllib-parse-ok/`（`from urllib.parse import urlparse`——stdlib 顶级模块判定反例保护，0 finding）。

> 注：预期退出码与 finding 数是设计目标，实现阶段以实际运行为准校准，偏离需在 PR 说明。#4 与 `line-499/` 的填充行由实现阶段用脚本生成后**以 Write 工具落盘**，不用 Bash 循环写文件。

---

## 8. 测试矩阵（8 触发 + 4 非触发 + 1 端到端）

### 8.1 触发测试（T1–T8）

| ID | 用户输入（示意） | 预期行为 |
|----|----------------|---------|
| T1 | "评估一下这个 skill 包能不能发布" | 触发；全量 E1–E12 评估 |
| T2 | "检查这个 skill 的 SKILL.md 是否符合规范" | 触发；E1–E4 |
| T3 | "这个 skill 的脚本有没有引入第三方依赖" | 触发；E5（AST 检查） |
| T4 | "帮我看看这个 skill 目录结构全不全" | 触发；E10–E12 |
| T5 | "装之前先检查这个第三方 skill 的质量" | 触发；全量评估（静态） |
| T6 | "这个 skill 的 fixtures 契约完整吗" | 触发；E9 |
| T7 | "按 novera 规范评估这个 skill" | 触发；--profile novera（8+4+1 计数） |
| T8 | "输出这个 skill 的评估 JSON 报告" | 触发；--format json |

### 8.2 非触发测试（N1–N4）

| ID | 用户输入（示意） | 预期行为 |
|----|----------------|---------|
| N1 | "扫描这个 skill 有没有后门和窃密逻辑" | 不触发（skill-sentry 职责：恶意行为检测） |
| N2 | "分析这个 skill 的依赖来源和维护者画像" | 不触发（skill-supply-chain-audit 职责） |
| N3 | "给这个 skill 仓库搭一套 CI workflow" | 不触发（仓库工程任务，非包评估） |
| N4 | "给这批 skill 打分排名，看哪个最好" | 不触发（无主观评分红线，如实拒绝） |

### 8.3 端到端测试（E1）

对 `fixtures/e2e-demo/` 完整走一遍：文本模式断言退出码 = 1、finding 数 = 1（E5）、报告含 profile/checks 计数行、finding 含 file:line 与 basis；JSON 模式断言可解析且 finding/stats 字段齐全；`--profile minimal` 对 `fixtures/minimal-ok/` 断言退出 0。

### 8.4 脚本级单元测试（CI 矩阵执行）

- fixtures #1–#14 全量跑：预期退出码逐一断言（#2 分别按 minimal/novera 两档断言；预期 exit 1 的用例一律 `if` 包裹）；
- `--only E5`：对 #7 断言只出 E5（不计 E6）；
- 反例保护：`comment-mention/`、`line-499/`、`urllib-parse-ok/` 断言 0 finding；
- 退出码 2：#14、不存在路径、`--only` 传非法检查 ID；
- AST 口径：验证注释/字符串中的 import 字样不触发、`urllib.parse` 不误报。

### 8.5 CI 写法强制约定

```bash
# 预期 exit 1 的唯一允许写法（if 包裹 + 成功则显式失败）
if python skills/skill-eval-harness/scripts/audit.py skills/skill-eval-harness/fixtures/bad-frontmatter/ > /dev/null; then
  echo "::error::expected exit 1, got 0"; exit 1
fi
# 注意：不允许 `|| true`（会把 exit 2 也吞成"通过"）
```

自举说明（设计取舍）：本 skill 落地后，`skills-ci.yml` 可选新增一步——用 eval-harness 评估本仓库每个 skill（`python skills/skill-eval-harness/scripts/audit.py skills/<slug>/`）。这是**对产品的额外验证**，不改变"仓库门禁归 CI、harness 是独立产品"的分工（A2）；是否启用由 team-lead 决定，本文档只预留。

---

## 9. 硬约束核对清单（本 skill 设计 × 全局 10 条）

| 约束 | 落位 |
|------|------|
| 纯标准库零依赖，3.9+ | §5.1 全部标准库；stdlib 清单内置（A7）；E7 即 3.9 门禁的产品化；CI py39 门禁 |
| 退出码 0/1/2 | §5.3 |
| finding 带 file:line | §2.1/§3 Finding format；缺失类定位约定（A10） |
| 性能数字不预写 | 全文无性能声明；SKILL.md 红线显式禁止 |
| 外部事实 URL + 日期 + 证据强度 | §6 data-provenance.md（标准 URL 实现阶段核实后填入，延续 verified/unverified） |
| 目录结构四件套 | SKILL.md + agents/openai.yaml + scripts/ + references/ + fixtures/ |
| SKILL.md < 500 行 | §3 约 200 行，CI wc -l 门禁 |
| 确定性脚本优先 | §3 Workflow 第 2 步"全部 finding 由脚本产生" |
| 诚实文档红线 | A5 无主观评分；§2.2 无总评断言；§7 预期数以实际运行为准 |
| 预期 exit 1 用 if 包裹 | §8.5 |
| 夹具用 Write 工具逐个写 | §7 标注（实现阶段执行） |
| 目录数据纯数据模块 | §5.1 eval_rules.py（复用 directory_data.py 模式） |

---

## 10. 待用户确认项汇总

1. §1 解读假设 A1–A12 逐条核对（尤其是 A3 对恶意行为不定性、A6 双档 profile、A8 不运行第三方脚本）；
2. A6 的 novera 档 8+4+1 计数是否允许 ±0 容差（当前设计为精确匹配）；
3. A8 夹具契约约定（MANIFEST 清单文件 vs 文件名内嵌后缀）实现阶段定稿，是否有倾向；
4. §8.5 自举步骤（用 harness 评估本仓库 skill）是否在 v0.1 启用。

确认后进入实现阶段（排期由 team-lead 决定）。
