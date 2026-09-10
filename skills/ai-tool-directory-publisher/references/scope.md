# Scope / 与相邻 skill 的分工

novera-skills 产品线是"Trust layer for AI agents"。ai-tool-directory-publisher
只负责其中一格：**AI 工具目录提交材料的校验、跨目录一致性与提交状态跟踪**。

## 分工表

| 相邻 skill | 职责边界 | 与本 skill 的关系 |
|-----------|---------|------------------|
| **geo-evidence-audit**（novera-skills #1，已发布） | 文本资产中地理声称的自洽性审计 | 不重叠：listing 里若含地理声称（如"上海办公室"与 +1 电话矛盾），由 geo-evidence-audit 处理；本 skill 只管字段完整性/枚举/URL/一致性/状态，不做地理交叉检测。两者可先后独立运行于同一 listing |
| **skill-sentry**（已发布，独立仓库） | 本地运行时安全审计 | 不重叠：sentry 管"代码与运行时"，本 skill 管"提交材料" |
| **skill-supply-chain-audit**（novera-skills #4，规划中） | 来源侧供应链画像 | 不重叠：管"依赖从哪来"，不管"listing 是否齐全" |
| **monorepo-analyzer**（已发布，独立仓库） | 仓库整体结构分析 | 不重叠 |

## 本 skill 明确不做的事（三条红线 + 边界）

1. **不自动提交**：跨站提交需要账号、付款与人工确认；本 skill 只产出
   "可提交"的材料校验结论，提交动作由用户人工完成；
2. **不爬目录站**：不抓取目录站数据、不抓竞品 listing；各站要求来自内置
   快照（附 URL + 抓取日期 + 证据强度），不联网；
3. **不承诺收录**："提交 ≠ 收录"，材料全绿只是可提交；不提供排名/SEO 服务；
4. 不做文案改写/裁剪：超限字段由 LLM 层按快照裁剪，改写后必须回到脚本
   重新校验（闭环）；
5. 不做 listing 内地理声称检测（geo-evidence-audit 职责）；
6. 不输出性能数字（未实测不写）。

## 判定口诀

- 问"提交材料齐不齐 / 符不符合某站要求 / 各站 listing 是否一致 / 状态表对不对"
  → **本 skill**
- 问"自动提交 / 爬站 / 保证收录" → 拒绝（红线），可先跑材料校验
- 问"listing 里的地理信息是否自洽" → geo-evidence-audit
- 问"代码/依赖是否安全" → skill-sentry / skill-supply-chain-audit
