# Novera Skills — Trust layer for AI agents

Deterministic, offline **Agent Skills** for auditing the trustworthiness of AI-produced content and claims. Built on the open Agent Skills standard (`SKILL.md` + `agents/openai.yaml`), compatible across clients, zero third-party dependencies, pure Python standard library.

> Status: early and small on purpose. One skill is released; the rest are on a public roadmap. Code over claims.

## What is this

Each skill in this repository audits one class of claims that AI-generated assets tend to assert — geographic claims today, more to come. Everything runs offline with deterministic scripts: same input, byte-identical report. Findings always carry `file:line` locations, and every judgment that depends on external facts is labeled with an evidence strength instead of being asserted.

## Skills

| Skill | Status | One-liner |
|-------|--------|-----------|
| [`skills/geo-evidence-audit`](skills/geo-evidence-audit/SKILL.md) | **v0.1.0 released** | Audits geographic claims in text assets for internal consistency: phone country codes vs claimed cities, timezones, currencies, coordinates vs country bounding boxes, hreflang tags, map embeds — and labels every claim with an evidence strength (explicit / inferred / unverified). |
| [`skills/ai-tool-directory-publisher`](skills/ai-tool-directory-publisher/SKILL.md) | **v0.1.0 released** | Prepares and audits AI tool directory submissions: validates listing materials against per-directory requirement snapshots (Futurepedia, Toolify, There's An AI For That, and more), finds drift between the same tool's listings across directories, and tracks submission status. Does NOT auto-submit, does NOT crawl, does NOT guarantee acceptance. |

## Roadmap

| # | Slug | Status | Scope |
|---|------|--------|-------|
| 1 | `geo-evidence-audit` | **released** (v0.1.0) | Geo-claim consistency audit |
| 2 | `ai-tool-directory-publisher` | **released** (v0.1.0) | Directory-submission materials, cross-directory consistency, submission status |
| 3 | `skill-eval-harness` | planned | Scope being defined |
| 4 | `skill-supply-chain-audit` | planned | Source-side supply-chain profiling for third-party skills (repository health, script network/install surface, permissions, distribution risk) — complements [skill-sentry](https://github.com/whaojie797-design/skill-sentry), which audits skills at runtime locally |
| 5–10 | *to be defined* | planned | Names and scope not yet fixed |

## Quick start (geo-evidence-audit)

No installation. Python 3.9+ required, nothing else.

```bash
# Text report
python skills/geo-evidence-audit/scripts/audit.py path/to/page-or-dir

# JSON report
python skills/geo-evidence-audit/scripts/audit.py path/to/page-or-dir --format json

# Only contradictions, drop unverified claims
python skills/geo-evidence-audit/scripts/audit.py path/to/page.md --min-strength explicit
```

Exit codes: `0` no findings · `1` findings present (contradictions or unverified claims) · `2` usage or input error.

As an Agent Skill, point your client at `skills/geo-evidence-audit/` — `SKILL.md` carries the trigger conditions, `agents/openai.yaml` the cross-client description.

## Repository layout

```
novera-skills/
├── skills/<slug>/        # one self-contained skill per directory:
│   ├── SKILL.md          #   triggers, workflow, boundaries (frontmatter: name + description only)
│   ├── agents/openai.yaml
│   ├── scripts/          #   deterministic stdlib-only tooling, entry audit.py
│   ├── references/       #   data provenance (URL + retrieval date + evidence strength), rules, evidence model, scope
│   └── fixtures/         #   audit test fixtures with expected exit codes
├── tests/<slug>/         # pytest suite driving the real CLI
├── tools/py39_gate.py    # CI syntax gate (ast feature_version=(3,9))
└── docs/                 # internal design docs (Chinese, not part of any release)
```

Skills directories intentionally contain **no README, install guide, or changelog** — everything consumer-facing lives here.

## Per-skill publishing

Each skill is versioned and released independently with a namespaced tag:

```
<slug>-v<semver>     e.g. geo-evidence-audit-v0.1.0
```

MAJOR = breaking change to triggers / CLI / output schema · MINOR = new signals, rules, or report fields · PATCH = false-positive/negative fixes, docs, fixtures. Bare `v*` tags and floating `latest` are never used. To consume a single skill, fetch the tag and take its `skills/<slug>/` directory.

## Constraints

- Pure Python standard library, zero third-party dependencies, Python 3.9+ (CI-enforced syntax gate)
- Fully offline: audit scripts never make network requests
- Deterministic: same input produces byte-identical output
- Findings always carry `file:line`; evidence strength is labeled, not asserted
- No performance claims anywhere: numbers only after they are measured
- CI gates: py39 syntax, stdlib-only import scan, SKILL.md < 500 lines, full pytest matrix (ubuntu/windows × 3.9/3.12)

## License

[MIT](LICENSE)

---

# Novera Skills — AI 智能体的信任层

确定性的、完全离线的 **Agent Skills**，用于审计 AI 产出内容与声称的可信度。基于开放 Agent Skills 标准（`SKILL.md` + `agents/openai.yaml`），跨客户端兼容，零第三方依赖，纯 Python 标准库实现。

> 状态：刻意保持早期与小体量。已发布一款，其余在公开路线图上。代码先于声称。

## 这是什么

本仓库的每款 skill 审计一类 AI 生成资产容易出错作假的声称——当前是地理声称，后续扩充。全部检测由离线的确定性脚本完成：相同输入，逐字节相同的报告。每条 finding 必带 `file:line` 定位；任何依赖外部事实的判断都标注证据强度，而不是直接断言。

## 技能列表

| 技能 | 状态 | 一句话说明 |
|------|------|-----------|
| [`skills/geo-evidence-audit`](skills/geo-evidence-audit/SKILL.md) | **v0.1.0 已发布** | 审计文本资产中地理声称的内部一致性：电话区号与声称城市、时区、货币、坐标与国家外包框、hreflang 标记、地图嵌入的交叉核对，并为每条声称标注证据强度（explicit / inferred / unverified）。 |
| [`skills/ai-tool-directory-publisher`](skills/ai-tool-directory-publisher/SKILL.md) | **v0.1.0 已发布** | 为 AI 工具目录站准备与审计提交材料：按各站字段要求快照（Futurepedia、Toolify、There's An AI For That 等）校验 listing 材料、发现同一工具跨目录信息漂移、维护提交状态表。不自动提交、不爬站、不承诺收录。 |

## 路线图

| # | Slug | 状态 | 范围 |
|---|------|------|------|
| 1 | `geo-evidence-audit` | **已发布**（v0.1.0） | 地理声称一致性审计 |
| 2 | `ai-tool-directory-publisher` | **已发布**（v0.1.0） | 目录站提交材料、跨目录一致性、提交状态 |
| 3 | `skill-eval-harness` | 规划中 | 范围定义中 |
| 4 | `skill-supply-chain-audit` | 规划中 | 第三方 skill 的来源侧供应链画像（仓库健康度、脚本网络/安装面、权限、分发风险）——与 [skill-sentry](https://github.com/whaojie797-design/skill-sentry)（本地运行时审计）互补 |
| 5–10 | *待定* | 规划中 | 名称与范围尚未确定 |

## 快速开始（geo-evidence-audit）

无需安装。仅需 Python 3.9+。

```bash
# 文本报告
python skills/geo-evidence-audit/scripts/audit.py path/to/page-or-dir

# JSON 报告
python skills/geo-evidence-audit/scripts/audit.py path/to/page-or-dir --format json

# 只要矛盾类 finding，过滤 unverified 声称
python skills/geo-evidence-audit/scripts/audit.py path/to/page.md --min-strength explicit
```

退出码：`0` 无 finding · `1` 有 finding（矛盾或 unverified 声称）· `2` 用法或输入错误。

作为 Agent Skill 使用时，将客户端指向 `skills/geo-evidence-audit/`——`SKILL.md` 载明触发条件，`agents/openai.yaml` 提供跨客户端描述。

## 仓库布局

```
novera-skills/
├── skills/<slug>/        # 每款 skill 自成一体的目录：
│   ├── SKILL.md          #   触发条件、工作流、边界（frontmatter 仅 name + description）
│   ├── agents/openai.yaml
│   ├── scripts/          #   确定性纯标准库工具，入口 audit.py
│   ├── references/       #   数据来源（URL + 抓取日期 + 证据强度）、规则、证据模型、分工
│   └── fixtures/         #   审计测试夹具与预期退出码
├── tests/<slug>/         # 驱动真实 CLI 的 pytest 套件
├── tools/py39_gate.py    # CI 语法门禁（ast feature_version=(3,9)）
└── docs/                 # 内部设计文档（中文，不进任何发布物）
```

skill 目录内刻意不放 **README、安装指南、变更日志**——面向使用者的信息全部在本文件。

## 按目录发布

每款 skill 独立版本化，用带 slug 前缀的 tag 发布：

```
<slug>-v<semver>     如 geo-evidence-audit-v0.1.0
```

MAJOR = 触发语义 / CLI / 输出结构破坏性变更 · MINOR = 新增信号、规则或报告字段 · PATCH = 误报漏报修复、文档、夹具。永不使用裸 `v*` tag 和浮动 `latest`。只需单个 skill 时，取对应 tag 下的 `skills/<slug>/` 目录即可。

## 工程约束

- 纯 Python 标准库，零第三方依赖，Python 3.9+（CI 语法门禁强制）
- 完全离线：审计脚本绝不发起网络请求
- 确定性：相同输入产生逐字节相同的输出
- finding 必带 `file:line`；证据强度只标注、不断言
- 任何地方不做性能声明：实测之后才写数字
- CI 门禁：py39 语法、纯标准库 import 扫描、SKILL.md < 500 行、全量 pytest 矩阵（ubuntu/windows × 3.9/3.12）

## 许可证

[MIT](LICENSE)
