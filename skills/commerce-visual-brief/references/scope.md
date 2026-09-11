# Scope - commerce-visual-brief

novera-skills 家族分工边界。本 skill 只管**电商视觉 brief 文档的材料质量**
（字段完整性、跨字段一致性、图片规格声明对照、极限词风险提示）。

## 四条边界

1. **geo-evidence-audit**：brief 里若出现地理/产地声称（"新疆长绒棉"、
   "意大利进口"）的真伪核验，归 geo-evidence-audit；本 skill 只把产地类
   文本当普通字段读，不核实其真实性。

2. **ai-tool-directory-publisher**：目录站 listing 的提交与校验归它。
   brief ≠ listing：brief 是给摄影/设计团队的内部需求单，listing 是面向
   目录站/平台的外部提交物。两边的字段基线与规则互不适用。

3. **skill-eval-harness**：skill 包结构自举评估归它（本包按其 novera 档
   0 finding 编写），与 brief 文档校验无关。

4. **skill-supply-chain-audit**：来源侧审计（依赖来源、数据来源链）归它；
   本 skill 的快照 provenance 记录在自家 references/data-provenance.md，
   不需要也不应该用 supply-chain-audit 来审计 brief 文档。

## 判定口诀

- 对象是**拍摄/设计需求单文档** → 本 skill。
- 要**生成**需求单 → 不触发；引导按 references/brief-template.md 撰写后
  回本 skill 校验（闭环）。
- 对象是**图片文件本体** → 不触发（本 skill 不读图片）。
- 对象是**目录 listing / 地理声称 / skill 包 / 来源链** → 各自归位。
