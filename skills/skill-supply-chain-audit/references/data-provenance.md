# Data provenance / 来源与核实记录

> 快照会过期，结论以抓取时点为准。verified 表示"官方文档页已访问并核对到
> 所述内容"，不保证当前仍为最新。

## GitHub REST API 端点文档（抓取日期：2026-09-11）

| # | 端点 | 文档 URL | 状态 | 核实内容 |
|---|------|----------|------|---------|
| 1 | GET /repos/{owner}/{repo} | https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28 | **verified** | 页面标题 "REST API endpoints for repositories"；Get a repository 的 200 示例含 archived / fork / open_issues_count / pushed_at / created_at |
| 2 | GET /repos/{owner}/{repo}/commits | https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28 | **verified** | 页面标题 "REST API endpoints for commits"；List commits 返回项含 commit.author.date 与 commit.committer.date（ISO 8601） |
| 3 | GET /repos/{owner}/{repo}/releases | https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28 | **verified** | 页面标题 "REST API endpoints for releases"；List releases 返回项含 tag_name / published_at；文档注明不含未关联 release 的普通 Git 标签 |
| 4 | GET /repos/{owner}/{repo}/contributors | https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-repository-contributors | **verified（页面级）** | 页面存在且目录含 "List repository contributors" 锚点。**字段级 unverified**：两次抓取正文均在到达该章节前截断，contributions / author 对象字段未能在响应示例中核对。实现因此按宽松 schema 处理（login/name/email/id 任一可用即去重，字段缺失不报错） |

## SARIF 2.1.0（抓取日期：2026-09-11）

- 标准文档：https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html — **verified**。
  "Static Analysis Results Interchange Format (SARIF) Version 2.1.0"，OASIS Standard，
  2020-03-27 发布。核实内容：sarifLog → runs[].tool.driver + results[]；result 对象含
  ruleId / level（error, warning, note）/ message / locations；
  physicalLocation = artifactLocation（uri）+ region（startLine）。
- `$schema` URI 采用 https://docs.oasis-open.org/sarif/sarif/v2.1.0/cos02/schemas/sarif-schema-2.1.0.json
  （标准前言指明 JSON schemas 位于该 cos02/schemas/ 路径；schema 文件本身未逐字抓取，
  该 URI 引用标 **unverified**——诚实标注）。

## 本 skill 内置数据清单的来源状态

| 数据 | 位置 | 状态 |
|------|------|------|
| 知名 skill 名清单（WELL_KNOWN_SKILLS） | scripts/chain_rules.py | **unverified（组织内约定）**：v0.1 仅收录 novera 仓库自有及文档中规划的 skill 名（本仓库 whaojie797-design/novera-skills 三款 + 规划中的 skill-sentry）。公开 registry / 市场的知名 skill 目录在实现阶段未找到可核实的官方清单源，按诚实红线不编造、不收录 |
| registry 白名单（REGISTRY_ALLOWLIST） | scripts/chain_rules.py | **default_convention: true**：pypi.org / files.pythonhosted.org / registry.npmjs.org / npmjs.com / www.npmjs.com / yarnpkg.com / registry.yarnpkg.com 为公知默认官方域，但作为"官方"清单是起草约定，不是经核实的权威名录 |
| 健康度阈值（stale 180d / 最低维护者 2 / release 窗口 365d / open 占比 0.8 / 仿冒编辑距离 2） | scripts/chain_rules.py | **default_convention: true**（每项）：起草默认值，非实测非事实，报告中逐条标注 |

## 快照时效声明

本 skill 全部来源判断基于用户提供的快照。快照抓取时点以 repo.json 的
fetched_at 为锚；缺失该字段时以本机日期为基准并在报告标注 "unverified"。
快照之外的任何实时状态，本 skill 不做断言。
