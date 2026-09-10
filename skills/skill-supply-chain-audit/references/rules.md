# Rules / S1–S10 判定逻辑

输入（按子命令）：profile = gh api 快照集；refs / chain = skill 包目录（必须含
SKILL.md）。输出：Finding 列表（排序键 `file, line, rule`，同输入逐字节同输出）+
清单（refs 专有）+ 输入警告（warnings）。警告不是 finding，不计入退出码。

## 阈值表（全部 default_convention: true，非事实断言）

| 阈值 | 默认值 | 用于 |
|------|--------|------|
| stale_days | 180 天 | S1 |
| min_maintainers | 2 人 | S2 |
| release_window_days | 365 天 | S3 |
| max_open_ratio | 0.80 | S4 |
| impersonation_max_distance | 编辑距离 2 | S10 |

使用任何阈值产生的 finding 必须在 basis 行写明
"… is a default convention (see references/rules.md), not a fact"。

## profile 组（快照 → 推理，强度 inferred）

### S1 stale-repo
- 最后提交时点 = commits 快照内最大 commit.committer.date（缺失回退
  commit.author.date，再回退 repo.pushed_at）；
- 时间锚点 = 快照 fetched_at 优先；缺失或不可解析 → 本机日期并全局标注
  "unverified"（不视为输入错误）；
- 距锚点天数 > stale_days → 报 1 条，signal 携带快照原始值与锚点日期；
- 最后提交晚于锚点 → 快照不一致，警告 + 不报。
- finding 锚定 repo.json 中 "pushed_at" 键所在行。

### S2 single-maintainer
- 贡献者去重：login → name → email → id 逐级取键（contributors 端点字段级
  unverified，故宽松处理）；
- 去重数 < min_maintainers → 报 1 条（锚定 contributors 文件 :1）；
- 空数组且 fetched_at 早于 repo.created_at → 数据未拉全，报输入警告、跳过 S2。

### S3 no-recent-release
- 未提供 releases 快照 → 输入警告 + 不可判定，不报；
- releases 为空数组 → 报 1 条 "no release ever published"；
- 最新 published_at 距锚点 > release_window_days → 报 1 条；
- published_at 全部不可解析或晚于锚点 → 警告 + 不报。

### S4 high-open-ratio
- 需要 repo 快照同时含 open_issues_count 与 closed_issues_count
  （后者非 gh api 标准字段；缺失 → 输入警告"不可判定"，不报——诚实处理）；
- open / (open + closed) > max_open_ratio → 报 1 条（锚定 open_issues_count 键行）。

### S5 archived-or-fork
- repo.archived == true → 报 1 条（锚定 archived 键行）；
- repo.fork == true → 另报 1 条（锚定 fork 键行）。

## refs 组（字面事实，强度 explicit；清单与 finding 分离）

- 扫描范围：SKILL.md、references/*.md|*.yaml|*.txt、agents/openai.yaml 逐行；
  scripts/*.py 仅 AST 字符串常量（不做文本 grep，注释/多行拼接天然免疫）；
- **清单**：全部外部 URL（文档行 https/http + 脚本字面量端点）逐项列
  `[inventory] file:line  url  (kind)`，附固定声明"清单 ≠ 风险；端点安全性不在
  本 skill 判定范围"；清单项不计入退出码；
- **S6 plaintext-endpoint**：URL 为 `http://` 且 host 非 localhost/127.0.0.1/
  0.0.0.0/[::1] → 报（文档行与脚本字面量均查）；
- **S7 raw-ip-endpoint**：脚本字符串字面量命中 IP 直连端点（`http://IP` 或
  `IP:port` 形态，纯版本号文本不误报）→ 报。IP 每段需 0–255 校验防误报。

## chain 组

### S8 risky-install-pattern（explicit，双条件）
- 条件一（模式）：行命中 curl/wget … | sh|bash|zsh|python 管道模式；
- 条件二（语境抑制）：命中行**同行**含否定/引述词（avoid、do not、never run/
  pipe、不要、切勿、不推荐、危险、反例、禁止等），或命中行位于围栏代码块内
  且**紧邻 fence 的最近非空文本行**含上述词 → 判定为文档化反面示例，抑制不报；
- 其余命中 → 报 1 条，signal 携带命中文本（截断 80 字符）。
- 独立安装代码块不受文档他处否定句影响（避免过度抑制）。

### S9 package-manager-prompt（explicit）
- 行命中 pip/pipx/npm/yarn/pnpm install/add 提示语，且该行显式携带 registry
  标记（--index-url / -i / --extra-index-url / --registry / @host/ 前缀）；
- 提取的 host 不在 REGISTRY_ALLOWLIST → 报 1 条；未显式指定 registry 的默认
  安装提示不报（即官方 registry 反例保护）。

### S10 name-impersonation（inferred）
- 候选名：SKILL.md frontmatter name、agents/openai.yaml name、包目录名、
  （--against 提供时）remote 文本中的 repo 名；大小写不敏感去重；
- 对 WELL_KNOWN_SKILLS 逐项计算编辑距离（Levenshtein，标准库 DP 实现）；
- 与某知名名**完全一致** → 不报（那是知名 skill 本尊，S10 反例保护）；
- 编辑距离 ≤ impersonation_max_distance → 报 1 条，signal 携带双方名称与
  距离值，basis 标注阈值为默认约定；
- 每个 distinct 候选名最多报知名清单中每个命中项 1 条，不做跨源重复。

## 反例保护清单（不触发）

1. `https://` 正常链接（S6 只查明文 http）；
2. localhost/回环地址的 http URL（非外部端点，仅进清单）；
3. 否定/引述语境的 curl|sh（S8 双条件，见上）；
4. 默认官方 registry 的安装提示（S9）；
5. 与知名清单完全一致的名称（S10）；
6. contributors 空数组 + fetched_at 早于仓库创建日（数据未拉全 → 输入警告）；
7. 快照缺 closed_issues_count / releases 未提供（S4/S3 不可判定 → 警告不硬报）。

## 退出码

- 0：无 finding（清单、警告的存在不影响）；
- 1：S1–S10 至少 1 条；
- 2：用法或输入错误（快照非法/schema 不符/无 SKILL.md/参数非法/缺子命令）。
  优先级 2 > 1 > 0。
