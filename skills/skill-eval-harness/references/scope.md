# Scope / 三条分工边界

skill-eval-harness 是评估**任意第三方 Agent Skill 包**结构质量的独立产品。
与三个相邻主体的分工如下（设计假设 A2/A3/A4）。

## 边界一：本仓库自身 CI（tools/py39_gate.py + skills-ci.yml）

- CI 管的是 **novera-skills 仓库自己的门禁**：py39 语法门禁、零依赖 grep、
  夹具回归、SKILL.md wc -l 门禁；
- eval-harness 是**装进用户环境后评估任意 skill 目录**的独立 skill 产品；
- 两者共享检查**思想**（AST、if 包裹、file:line），不共享运行时代码、互不
  调用。CI 可选地用 harness 评估本仓库 skill（自举），那是对产品的额外
  验证，不改变分工。

## 边界二：skill-sentry（恶意行为审计）

- sentry 管**恶意行为**：窃密、后门、破坏性操作、运行时行为分析；
- eval-harness 管**结构与质量合规**：存在性/计数/枚举/AST 事实；
- harness 对"脚本是否有恶意"不做任何判断——哪怕包里出现网络调用，也只报
  "违反结构规范"（issue 固定附 "no behavior verdict"），不定性为恶意。

## 边界三：skill-supply-chain-audit（来源侧供应链画像）

- supply-chain 管**来源侧**：包的出处、依赖来源、维护者画像；
- eval-harness 管**包内现状**：目录里实际有什么、合不合规；
- harness 评估全程**不联网**、不追溯任何包的来源。

## 本 skill 明确不做的事（红线）

1. 不执行被评估 skill 的任何脚本（静态评估边界）；
2. 不联网（eval_rules 的标准库清单、规范 URL 均为内置快照）；
3. 不做主观评分：无总分、无星级、无排名、无总评断言；
4. 不修改被评估包的任何文件；
5. 不输出性能数字（未实测不写）。

## 判定口诀

- 问"这个 skill 包结构合不合规 / 发布前自查 / 安装前检查" → **本 skill**
- 问"这个 skill 有没有后门恶意" → skill-sentry
- 问"这个 skill 从哪来、谁维护" → skill-supply-chain-audit
- 问"给仓库搭 CI / 改门禁" → 仓库工程任务，不是包评估
- 问"给一批 skill 打分排名" → 拒绝（无主观评分红线）
