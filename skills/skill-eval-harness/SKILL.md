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
