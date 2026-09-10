# Rules / 校验规则（V1–V5 / C1 / S1）

输入：listing 文件（JSON / YAML 最小子集 / Markdown frontmatter）解析出的
带行号字段，或状态表（CSV / JSON）行。
输出：Finding 列表，排序键 `(file, line, rule)`，同输入逐字节同输出。

## 目录解析（listing → directory spec）

1. listing 内显式 `directory` 字段（值为 slug）优先；
2. 否则按文件名包含的 slug 标记匹配（如 `futurepedia.json` → futurepedia；
   taaft 别名含 `theres-an-ai-for-that`，其余见 directory_data.py file_tokens）；
3. 均无 → 对**全部 verified 目录快照**各跑一遍，完全相同的 finding 去重为一条
   （锚定字母序第一个 slug 的措辞）；
4. `--directory SLUG` 显式指定时只跑该 slug。

## V1 missing-required-field

- 触发：快照标记 required 的字段缺失。finding 锚定在文件第 1 行（缺失字段无
  所属行），value 记 `(missing)`。
- 强度：快照 verified → explicit；unverified 快照 → unverified（默认不跑）。

## V2 field-length-out-of-range

- 触发：字段长度（字符数；features 按列表项数）落在快照 min/max 区间外。
- 区间两端可单边生效（如 features 只有 min=0）。

## V3 invalid-enum

- pricing：值不在 free/freemium/paid/subscription → finding。枚举匹配
  **大小写不敏感**（"Free" 合规；"free-tier" 违规），这是 pricing 大小写
  反例保护的一半（另一半在 C1）。
- category：值不在快照枚举 → finding。

## V4 invalid-url

- 触发：url 字段存在但不是 `http(s)://` 绝对地址、含空格或缺 scheme。
- 通用格式规则，不依赖快照。

## V5 screenshot-spec-mismatch

- 触发：screenshot 声明中可解析出 `宽x高` 尺寸，且低于快照规格
  （PNG/JPG、横版、最小 1280x720）。
- 反例保护：声明中无可解析尺寸时**不触发**（宁漏报不误报）。

## C1 cross-listing-drift（一致性 diff）

- 锚点四项：**name、url、pricing、version**。
- 仅当两侧字段都存在且归一化后不同才触发：
  - pricing 归一化为小写（Free vs free 不触发）；
  - url 去尾部斜杠后比较；name/version 精确比较（仅去首尾空白）。
- finding 锚定在偏离侧的 file:line，value/expected 附两侧 file:line 与原值，
  强度 inferred。
- 不做语义 diff：description 漂移只在可字面判定时才有意义（v0.1 未实现
  description 内嵌旧版本号/旧 pricing 字样的检测，见已知局限）。

## S1 status-table-integrity

- 状态枚举：status 必须属于 draft / submitted / under-review / listed /
  rejected（大小写不敏感）。
- 日期：date 必须是 ISO 8601 日期（YYYY-MM-DD，且必须是真实存在的日期，
  如 2026-13-01 不合规）。
- listing 覆盖（可选能力）：当调用方提供 listing 文件列表时，每个 listing
  文件名主干必须至少被一行 `tool` 记录覆盖；CLI `status TABLE` 不扫描
  listing 文件，此检查不激活。
- 反例保护：同一工具的合理重复提交记录（rejected → submitted）**不**触发——
  状态表不施加 tool+directory 唯一性约束。

## 已知局限

1. YAML 只支持最小子集（扁平键值 + 一层列表）；嵌套、锚点、内联 dict 报
   "未支持"（返回无结构 → 退出码 2）；
2. JSON 只支持顶层扁平对象（标量 / 标量列表值）；嵌套对象报"未支持"；
3. Markdown 只解析 frontmatter 与正文中的 `- key: value` 行；H2 段落式
   字段不识别；
4. C1 不做语义级 diff（离线确定性约束，宁漏报不误报）；
5. 快照数值为编制基线，官网未公布数字，一切以官网为准（见
   data-provenance.md）。
