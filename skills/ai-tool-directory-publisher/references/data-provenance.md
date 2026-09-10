# Data Provenance / 目录站快照来源与证据强度

本文件记录 `scripts/directory_data.py` 内置的 6 家 AI 工具目录站快照的来源、
核实结果、URL、抓取日期与证据强度。

**统一抓取/核实日期：2026-09-10。**

> **显式声明：目录站字段要求随时可能变化，一切以各站官网为准。**
> 本快照只用于离线一致性预检，不构成对任何目录站要求的权威转述。

## 证据强度标注约定

- **explicit（已核实）**：实现期通过 WebFetch 访问该站官方页面，直接观察到的
  事实（提交入口存在、付费模式、表单字段、审核机制），来源 URL 可复核
- **unverified / 合理归纳（未逐项核实）**：官方页面**未公布具体数字**的字段
  约束（长度区间、category 枚举、截图规格），由本 skill 按行业惯例编制的
  基线。directory 级 `verified=true` **不等于**这些数字经官网逐项确认

## 逐站核实结果表

| slug | 站点名 | verified | 官方来源 URL | 抓取日期 | 已核实事实（explicit） | 编制基线（unverified） |
|------|--------|----------|-------------|---------|----------------------|----------------------|
| futurepedia | Futurepedia | **true** | https://www.futurepedia.io/submit-tool ；https://www.futurepedia.io/verified | 2026-09-10 | 提交入口存在；Basic listing $247（页面标注 Sold Out）/ Verified listing $497 一次性；编辑质量审核；HubSpot 提交表单；被拒全额退款 | 全部字段的长度区间、category 枚举、截图规格 |
| toolify | Toolify | **true** | https://www.toolify.ai/submit | 2026-09-10 | 提交表单字段：**Name**、**Website URL**；可选 "Do it myself — Provide tool information myself in English only"；$99，48 小时内上线 | 其余字段（tagline/description 等）的长度区间、category 枚举、截图规格 |
| taaft | There's An AI For That | **true** | https://theresanaiforthat.com/launch/ | 2026-09-10 | 提交/发布入口存在；$49 一次性审核费；永久 listing；编辑审核模式 | 全部字段的长度区间、category 枚举、截图规格 |
| topai-tools | TopAI.tools | **true** | https://topai.tools/submit | 2026-09-10 | Fast Track $47 一次性；编辑审核，未通过自动退款；工具须"AI-powered、fully functional、clear value"；FAQ 建议清晰描述与高质量截图 | 全部字段的长度区间、category 枚举、截图规格的具体数字 |
| ai-tools-directory | AI Tools Directory | **false** | https://aitoolsdirectory.com/submit （页面可达但无提交要求内容，仅订阅入口）；https://aitoolsdirectory.com/add-listing （404） | 2026-09-10 | 无可直接核实的要求 | 整站快照为合理归纳，**默认不参与校验** |
| aitools-fyi | AITools.fyi | **false** | https://aitools.fyi/submit （重定向至第三方 "Boost My Tool" 代提交服务，其表单字段 Email/Tool Link/Tool Name/Tool Description/Pricing 属第三方流程，非 AITools.fyi 官方要求） | 2026-09-10 | 无可直接核实的要求 | 整站快照为合理归纳，**默认不参与校验** |

## 核实成功判定

4/6 家（futurepedia、toolify、taaft、topai-tools）在实现期成功访问官方
提交页并记录了可引用的要求，`verified=true`，支撑默认校验路径；2 家
（ai-tools-directory、aitools-fyi）无法从官方渠道核实要求，`verified=false`，
其快照默认跳过，需 `--include-unverified` 显式开启，finding 强度标 unverified。

## 编制基线（4 家 verified 站点共用，unverified）

| 字段 | required | 长度/规格 | 说明 |
|------|----------|----------|------|
| name | 是 | 1–60 字符 | |
| tagline | 是 | 10–60 字符 | |
| description | 是 | 50–1000 字符 | |
| category | 是 | 枚举（14 项，见 directory_data.py CATEGORY_ENUM） | |
| pricing | 是 | free/freemium/paid/subscription | 此枚举为**本 skill 设计固定**（V3），非站点声称 |
| features | 否 | ≥0 项（空列表允许） | |
| url | 是 | http(s) 绝对地址 | V4 格式规则与快照无关 |
| screenshot | 否 | PNG/JPG、横版、最小 1280x720 | |

## 已知局限

1. 官方页面均未公布字符级限制，上表数字为编制基线，**提交前必须以官网为准**；
2. Toolify 实际由 AI 生成大部分 listing 内容（"Do it myself" 仅为可选项），
   字段要求可能与常规目录不同；
3. 快照不含各站分类树（category 全量枚举远大于编制的 14 项基线）。

## 更新流程

1. 重新访问上表 URL，记录新抓取日期与观察事实；
2. 更新 `scripts/directory_data.py` 对应 DirectorySpec（纯数据）；
3. 同步更新本表；4. 跑完 fixtures 确认预期不回退；5. 变更记入根 README
（skill 目录内不放 CHANGELOG）。
