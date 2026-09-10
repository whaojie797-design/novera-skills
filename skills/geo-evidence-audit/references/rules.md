# Rules / 交叉检测规则（R1–R7）

输入：`extract.py` 提取的 7 类信号（phone / coord / place / currency /
timezone / locale / map），全部带 `file:line` 定位。
输出：`Finding` 列表，排序键 `(file, line, rule)`，保证同输入逐字节同输出。

## 信号配对（pairing）

R1–R4、R6 都需要把"某个地理信号"与"某个地点声称"配对后比较：

1. 地点声称按（名字, 国家）聚合为"声称"；同一声称的多次出现算一条
   （finding 锚定在最早出现行）；
2. 每个非 place 信号归属**行号距离最近**的地点声称（同距离取更早行、更早列）；
3. 没有分到任何信号的声称交给 R7 判断。

取此设计的动机：门店 JSON / CSV 每行一条记录，最近配对天然隔离各记录互不
串扰；散文式文档中信号与其所属声称在行号上也最接近。地图 URL 内部出现的
地名/坐标属于地图信号本身（由 R6 处理），不作为独立文本声称参与配对。

## R1 phone-vs-country

- 触发：地点声称国家 X（由城市/国名词表映射）+ 配对电话经 E.164 前缀解析
  属于国家集合 Y，且 X ∉ Y。
- 强度：inferred。推理链：`phone +1 (212) 555-0100 -> US,CA (inferred, via
  country calling code)`。
- 反例保护：`+1` 映射到 {US, CA}（NANP 共用），任一匹配即一致。

## R2 tz-vs-place

- 触发：地点声称国家 X + 配对时区信号（IANA 名或 `UTC±n` 偏移）的 UTC 偏移
  不在 X 的偏移列表内。
- 强度：inferred。推理链注明 `via UTC offset table`。
- 反例保护：多时区国家（美/俄/加等，见 `MULTI_TZ_COUNTRIES` 及各国
  `tz_offsets` 列表）任一偏移命中即一致——如美国办公室写 `UTC-7` 不触发。
- 局限：偏移取标准时间，不建模亚利桑那不用 DST 这类例外（宁漏报不误报）。

## R3 currency-vs-country

- 触发：地点声称国家 X + 配对货币信号（ISO 4217 代码或符号）的候选代码集合
  与 X 的法定货币集合无交集，且不满足欧元区例外。
- 强度：inferred。推理链注明 `via ISO 4217`。
- 反例保护：
  - 欧元区成员（`EUROZONE_MEMBERS`，含爱尔兰）使用 `€`/`EUR` 不触发；
  - 歧义符号（`$`、`¥`）按多候选处理，任一候选命中即一致。

## R4 coord-vs-country

- 触发：地点声称国家 X + 配对坐标（十进制或度分格式，归一为十进制）不落在
  X 的近似 bbox 外包框内。
- 强度：inferred。推理链固定注明 `approximate ... not precise reverse
  geocoding`——bbox 是国家级粗粒度外包框，可能含邻国边缘区域，**不是精确
  反地理编码**。
- 反例保护：未知国家或无 bbox 数据的国家一律不触发（宁漏报不误报）。

## R5 locale-vs-place

- 触发：页面级 locale 信号（`lang` / `hreflang` / `xml:lang` 属性）带区域
  子标签（如 `zh-CN` → CN），且该区域国家不在文件中任何地点声称的国家
  集合内。
- 强度：inferred。推理链注明 `via BCP47 region subtag`。
- 反例保护：纯语言标签（如 `fr`，无区域子标签）、未知区域代码不触发；
  多语言页面若声称覆盖多国，各地域标签只要命中任一声称国家即一致。

## R6 map-vs-place

- 触发：配对地图嵌入（Google Maps / OSM / Bing Maps URL 或 iframe src）：
  - `q=` 参数或 `@lat,lng` / `#map=z/lat/lon` 解析出地点或坐标；
  - 解析出的地点属国 ≠ 声称国 → finding（severity=error）；
  - 同国不同城 → finding（severity=warning）；
  - 解析出的坐标不在声称国 bbox 内 → finding（severity=error）。
- 强度：inferred。推理链注明 `via map URL parameter`；坐标类注明粗粒度 bbox。

## R7 unverified-claim（兜底）

- 触发：某地点声称**没有分到任何**配对信号（无论一致与否），且在整个互证
  范围（单文件模式=本文件；目录模式=同目录全部文件）内找不到与其声称国家
  **一致**的信号（电话区号命中、货币命中、IANA 时区名主属国命中、坐标入
  bbox、locale 区域命中、地图定位命中任一）。纯 UTC 偏移（如 `UTC+1`）被
  多国共享，不参与互证，避免"Berlin 的 UTC+1 佐证 Zurich"式假互证。
- 强度：unverified，severity=info。
- 语义边界：R7 只说"没有佐证"，**不等于声称虚假**；unverified ≠ false。
- 与 R1–R6 的分工：已卷入矛盾的声称（有相关信号）由对应规则报告，R7 不重复报。

## 已知局限汇总

1. bbox 误差（见 R4）；2. 标准时间基准、不做 DST 例外（见 R2）；
3. 城市词表非穷举，未收录地名不产生信号；4. `+1` 等 NANP 区号不区分美加；
5. 最近行配对是启发式：跨长文档、同国家多声称且信号归属歧义的排版可能漏报
   ——均按"宁漏报不误报"取舍。
