# Evidence Model / 证据强度模型

geo-evidence-audit 对文本资产中的每一条地理相关声称标注证据强度。四档定义：

| 强度 | 定义 | 在报告中的出现方式 |
|------|------|------------------|
| **explicit** | 信号被直接、无歧义地写出：`+86` 区号、完整坐标、IANA 时区名、ISO 货币代码、`lang="zh-CN"` 属性 | 提取出的信号（claimed 字段）全部为 explicit |
| **inferred** | 由交叉规则推导得出：如"电话属国由区号推得"。所有 R1–R6 的 finding 均为 inferred，conflict 字段内写明推理链（via country calling code / via UTC offset table / via ISO 4217 / via country bounding box / via BCP47 region subtag / via map URL parameter） | finding 的 strength 字段 |
| **unverified** | 同文件/同目录内找不到任何互证信号的地理声称（R7 兜底，info 级） | finding 的 strength 字段 |
| **未验证** | 脚本无法离线核实的外部事实（如"上海确有该办公室"）。本 skill 一律不做断言，只如实标注"未验证" | SKILL.md 与报告 notes 中说明，不产生具体数值 |

## 互证逻辑（corroboration）

- **互证范围**：单文件模式 = 该文件内全部信号；目录模式 = 同目录下全部被扫描
  文件的信号（目录是一个自然的"同一资产"边界）。
- **升级规则**：地点声称分到与其一致的其他地理信号（每个信号归属行号距离
  最近的声称；区号命中、货币命中、IANA 时区名主属国命中、坐标入 bbox、
  locale 区域命中、地图定位命中任一），即视为有互证，不再标 unverified。
- **降级/孤立**：配对窗口内没有任何相关信号、且互证范围内无一致信号的声称，
  标 unverified（R7）。
- **矛盾优先**：已卷入 R1–R6 矛盾的声称由对应规则报告；这些声称有"相关信号"
  （哪怕不一致），R7 不再对其重复报告，避免同一问题双计。

## unverified ≠ false（红线条目）

本 skill 审计的是**自洽性**，不是真值：

- "我们在 Zurich 有办公室"没有被其他信号佐证 → 报 R7 unverified；
- 这**不代表**该办公室不存在，只代表文本内部没有证据支撑它；
- 同理，R1–R6 的矛盾 finding 说明文本内部信号打架，不判断哪一方为真；
- 对外解释结果时，向用户明确这一边界：本工具不做任何联网核实，"真值核实"
  不在 v0.1 范围。

## 与 CLI 过滤的关系

`--min-strength` 按下限过滤 finding（explicit > inferred > unverified）：

- 默认 `unverified`：全量报告；
- `--min-strength inferred`：只看矛盾类，忽略孤立声称；
- `--min-strength explicit`：脚本产出的 finding 均为 inferred/unverified，
  因此结果恒为 0 finding（退出码 0），用于"只信直接证据"的严格口径。
