# Data Provenance / 评测标准来源与证据强度

本文件记录 `scripts/eval_rules.py` 内置检查项的规范依据来源、URL、抓取日期
与证据强度。延续 verified/unverified 快照机制。

## 逐项来源表

| 依据键 | 覆盖检查项 | 来源 | URL | 抓取日期 | 证据强度 |
|--------|-----------|------|-----|---------|---------|
| agent-skills-standard | E1（frontmatter 仅 name+description 的格式基线）、E10（agents/openai.yaml 为本仓库跨客户端约定，非开放标准要求）、包结构（SKILL.md 必需，scripts/references/assets 可选） | Agent Skills 开放标准官方站点（格式最初由 Anthropic 开发并作为开放标准发布） | https://agentskills.io/ | 2026-09-10 | **explicit（已核实）**：官方页面直接观察——"a skill is a folder containing a SKILL.md file. This file includes metadata (name and description, at minimum)"；目录结构 SKILL.md（必需）+ scripts/、references/、assets/（可选） |
| novera-profile-conventions | E2（<500 行预算）、E3（novera 档 8+4+1 计数）、E4（退出码 0/1/2 声明）、E5–E7（纯标准库/禁网络 spawn/py39 语法）、E8（finding 带 file:line）、E9（MANIFEST.tsv 夹具契约）、E12（禁 README*/CHANGELOG*/INSTALL*） | 本组织《通用前缀规范》与 novera-skills 仓库工程约束（内部约定，无外部 URL） | 无（组织内部规范） | — | **unverified（组织内约定）**：这些数字是 novera 档的组织规范，不声称是 Agent Skills 开放标准的要求；第三方包不满足时属"与 novera 档不合"，不代表违反开放标准（可用 minimal 档评估） |

## 已核实事实引用（agent-skills-standard，2026-09-10 抓取）

- "At its core, a skill is a folder containing a `SKILL.md` file. This file
  includes metadata (`name` and `description`, at minimum) and instructions
  that tell an agent how to perform a specific task."
- 目录结构示例：`SKILL.md`（Required: metadata + instructions）、`scripts/`
  （Optional: executable code）、`references/`（Optional: documentation）、
  `assets/`（Optional: templates, resources）。
- 推论映射：E1 检查的"frontmatter 仅 name+description"比开放标准的"at
  minimum"**更严格**——这是 novera 档的组织纪律（frontmatter 多字段报
  finding），第三方包若需放官认知可用 minimal 档。开放标准本身不禁止额外
  frontmatter 字段。

## Python 3.9 标准库清单（STDLIB_MODULES）

来源：CPython 3.9 官方标准库索引。URL: https://docs.python.org/3.9/library/
（抓取日期：2026-09-10）。清单为顶级模块名内置快照（3.9 无
`sys.stdlib_module_names`）；证据强度 explicit（官方索引事实），允许与
3.9 实际发行存在极小出入（评估脚本本身 3.9 门禁可校验）。

## 已知局限

1. agentskills.io 页面为开放标准概述，未规定行数预算、退出码语义等工程
   约束——E2/E4/E8 等 novera 档项的依据是组织内约定，如上表标注；
2. E9 的 MANIFEST.tsv 契约（`relpath<TAB>expected_exit`，expected ∈ 0/1/2）
   为本组织夹具契约约定（lead 裁决定稿），非开放标准内容；
3. 标准页面内容可能更新，重新引用时按"更新流程"重抓。

## 更新流程

1. 重访上表 URL 记录新抓取日期；2. 更新 eval_rules.py 对应常量；3. 同步本表；
4. 跑完 fixtures 确认预期不回退；5. 变更记入根 README（skill 目录内不放
CHANGELOG）。
