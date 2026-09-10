# Scope / 分工边界（四条）

## ① skill-sentry —— 恶意行为判定

skill-sentry 回答"包里有没有恶意代码"（注入、后门、窃密逻辑，本地运行时行为
分析）。本款输出的任何信号——curl|sh 安装提示、非官方 registry、IP 端点、
stale 仓库——都**不定性为恶意**：它们是与已知分发风险模式的字面相符，动机
与实际行为超出本款范围。反过来，sentry 也不负责来源侧画像。

## ② skill-eval-harness —— 包内结构质量

skill-eval-harness 回答"这个包的**现状**结构合规吗"（SKILL.md 规范、scripts
门禁、fixtures 契约、目录完整性）。本款回答"这个包的**来源**可靠吗"（谁维护、
从哪分发）。两款的输入、规则、输出互不重叠：harness 不看 gh api 快照，本款
不评 frontmatter 与 fixtures 质量。

## ③ geo-evidence-audit —— 地理声称自洽性

geo-evidence-audit 处理 SKILL.md/文档中的地理声称与佐证是否互洽（时区、坐标、
货币、电话区码）。与本款零交集：一个看内容里的地理事实，一个看来源与分发链路。

## ④ ai-tool-directory-publisher —— listing 材料一致性

ai-tool-directory-publisher 处理 AI 工具目录提交材料的生成、校验与跨目录
一致性（名称/版本/定价在各 listing 间是否一致）。与本款零交集：它管"提交
出去的材料对不对"，本款管"包从哪来、谁来维护"。

## 共同红线

四款同守：不联网（本款连输入都必须是用户提供的快照）、退出码 0/1/2
（2 严重 > 1 一般 > 0 通过）、finding 带 file:line、输出确定性、无评分无
总评、不修改用户文件。
