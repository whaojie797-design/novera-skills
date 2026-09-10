# Data Provenance / 数据来源与证据强度

本文件记录 `scripts/geo_data.py` 内置数据的来源、URL、抓取日期与证据强度标注。
这是硬约束"外部事实必须附 URL + 抓取日期 + 证据强度"的落点。

统一抓取日期：**2026-08-30**。更新任何一类数据时，必须同步更新本文件中的
URL、抓取日期与证据强度标注。

## 证据强度标注约定

- **explicit**：来自权威标准/官方发布的编码事实，可直接逐条核对
- **approximate（未验证/近似）**：粗估数据，存在已知误差，仅用于粗粒度判断

## 数据类别清单

| 数据类别 | 内容 | 来源 | URL | 抓取日期 | 证据强度 |
|---------|------|------|-----|---------|---------|
| 国家代码 | ISO 3166-1 alpha-2 两字母代码（`COUNTRIES` 键） | ISO 3166 Maintenance Agency / ISO Online Browsing Platform | https://www.iso.org/obp/ui/#search | 2026-08-30 | explicit |
| 国家区号 | ITU-T E.164 国家码（`calling_codes`） | ITU-T E.164 建议书分配表 | https://www.itu.int/rec/T-REC-E.164 | 2026-08-30 | explicit |
| 法定货币 | ISO 4217 货币代码（`currencies`） | ISO 4217 Currency Codes / Six Group 官方列表 | https://www.six-group.com/en/products-services/financial-information/data-standards.html | 2026-08-30 | explicit |
| 时区偏移 | 各国 UTC 偏移小时数、IANA 时区名 → 偏移（`tz_offsets`、`IANA_TZ_OFFSETS`） | IANA Time Zone Database（tzdata，标准时间，不含 DST 例外） | https://www.iana.org/time-zones | 2026-08-30 | explicit（标准时间基准；个别国家 DST/夏令制例外未建模，见下"已知局限"） |
| IANA 时区归属 | 时区名 → 主要国家（`IANA_TZ_COUNTRY`） | IANA tzdata zone.tab / zone1970.tab 字段 | https://www.iana.org/time-zones | 2026-08-30 | explicit（取该时区的主要归属国） |
| 欧元区成员 | 使用 EUR 为法定货币的国家集合（`EUROZONE_MEMBERS`） | European Central Bank 官方说明 | https://www.ecb.europa.eu/euro/intro/html/index.en.html | 2026-08-30 | explicit |
| 多时区国家 | 跨多个 UTC 偏移的国家集合（`MULTI_TZ_COUNTRIES`） | 由 tzdata 偏移表归纳（同上 IANA 来源） | https://www.iana.org/time-zones | 2026-08-30 | explicit（成员资格）；具体偏移列表见 tz_offsets 行 |
| 国家 bbox | 国家级经纬度外包框（`bbox`） | 依据公开地理百科与地图数据粗估整理 | 无单一权威 URL（合成数据） | 2026-08-30 | **approximate / 未验证**：仅作国家级粗粒度校验，可能包含邻国边缘区域（如美国 bbox 含部分加拿大水域）。**不是精确反地理编码** |
| 城市词表 | 各国代表性城市中英文名（`cities_en`/`cities_zh`） | 人工整理的代表性大城市清单（非穷举地名录） | 无单一权威 URL（人工整理） | 2026-08-30 | **approximate / 未验证**：覆盖各国主要城市，不保证全部地名变体；未收录城市不参与匹配（宁漏报不误报） |
| 国名别名 | 常见别名字典（`COUNTRY_ALIASES`，如 USA/UK/UAE） | 常识性简称整理 | 无单一权威 URL（人工整理） | 2026-08-30 | approximate / 未验证 |
| 货币符号 | 符号 → 可能的 ISO 4217 代码（`CURRENCY_SYMBOLS`，含歧义符号如 `$`、`¥`） | Unicode CLDR 典型用法 + ISO 4217 | https://cldr.unicode.org/ | 2026-08-30 | explicit（映射关系）；歧义符号按多候选处理，不会据此单独触发 finding |

## 已知局限（与数据来源直接相关）

1. **bbox 是外包框，不是边界**：`bbox` 只保证"框内点大概率属于该国或其近海"，
   反向结论（框内 → 属于该国）与框外判定均存在误差。R4/R6 的坐标类 finding
   一律在文本中注明 "approximate ... not precise reverse geocoding"。
2. **时区取标准时间**：`IANA_TZ_OFFSETS` 为标准时间偏移，不含亚利桑那不实行
   DST 这类例外建模（设计假设 A12：宁漏报不误报）。
3. **城市词表非穷举**：未收录的城市/地名不会产生 place 信号，不会误报，但会漏报。
4. **货币符号歧义**：`$`、`¥` 等符号对应多个国家的货币，任何候选匹配即视为一致。

## 更新流程

1. 从上表 URL 重新抓取对应数据（记录新的抓取日期）；
2. 更新 `scripts/geo_data.py` 对应常量（纯数据，无逻辑）；
3. 同步更新本表的 URL 与抓取日期；
4. 跑完 `fixtures/` 全量夹具确认预期退出码与 finding 数不回退；
5. 数据内容变更记入根 README 对应小节（skill 目录内不放 CHANGELOG）。
