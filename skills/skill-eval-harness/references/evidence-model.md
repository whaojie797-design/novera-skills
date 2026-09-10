# Evidence Model / 证据强度模型

## 四档定义

| 强度 | 定义 | 在本 skill 的出现方式 |
|------|------|---------------------|
| **explicit** | 包内可验证事实：存在性、计数、枚举、AST 节点。全部 E1–E12 finding 均为 explicit | finding 的 strength 字段 |
| **inferred** | 跨文件推导。v0.1 无此类检查，保留档位以对齐统一模型 | 不出现 |
| **unverified** | 检查项的**规范依据**尚未核实或属组织内约定（novera 档的 8+4+1、行数预算、MANIFEST 契约等）——此类检查项默认仍运行，但来源状态在 data-provenance 中如实标注 | data-provenance 的来源表，finding 的 basis 字段指向 references/rules.md |
| **未验证** | 任何"这个 skill 质量好不好 / 能不能被客户端采纳"的综合评价 | harness 一律不做断言 |

## 静态评估边界（红线条目）

1. **绝不运行被评估 skill 的任何脚本**。E5–E7 全部基于 AST 解析结果——
   解析不等于执行，恶意代码不会被触发。运行时行为审计归 skill-sentry 领域；
2. **对恶意行为不定性**：E6 检出网络/进程派生调用时，issue 文本固定为
   "structure violation only; no behavior verdict"——只说明该调用违反结构
   规范，不判断作者意图；
3. **不追溯来源**：harness 不联网、不查出处与维护者（那是
   skill-supply-chain-audit 的职责）；
4. **无总评**：不输出总分、星级、排名、pass/fail 单一结论字段——finding
   数与逐条明细本身就是判定依据；JSON 报告含 checks_run/checks_skipped
   计数与逐条 finding。

## 与 profile 的关系

- novera 档（默认）：12 项全跑，含 8+4+1 精确计数（组织规范）与 E8；
- minimal 档：11 项（E3 只查存在性、E8 跳过），保证对任意第三方包可用——
  第三方不满足 novera 组织规范不算"违反开放标准"（开放标准只要求
  SKILL.md + name/description，见 data-provenance）；
- `--only` 覆盖默认集合，报告头如实反映 checks run/skipped。

## 退出码语义（全局规范）

0 = 全部运行检查项通过；1 = 至少一条 finding；2 = 用法或输入错误（目录
不存在 / 无 SKILL.md / 参数非法 / `--only` 非法检查 ID）。优先级 2 > 1 > 0。
