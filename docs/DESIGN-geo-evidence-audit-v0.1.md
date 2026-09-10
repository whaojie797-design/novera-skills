# geo-evidence-audit v0.1.0 完整设计

> 设计人：软件架构师（高见远）
> 状态：设计稿，待用户核对 §1「解读假设」后定稿
> 所属：novera-skills mono-repo 第 1 款 skill（`skills/geo-evidence-audit/`）
> 本文档是设计，不含实现代码；文中代码块均为草案签名与格式约定。

---

## 1. 解读假设（供用户逐条核对纠偏）

原始提示词全文丢失，以下为本设计对名称 "geo-evidence-audit"（地理证据审计）的语义重构。**每条都可能被用户推翻，推翻后按 §11 修订流程更新设计。**

| # | 假设 | 依据与范围取舍 |
|---|------|---------------|
| A1 | "地理证据审计"指：对文本资产（md/html/json/csv 等）中的**地理相关声称**做一致性交叉检测，产出逐条 finding。是"文档审计"而非"地理数据质量工具"——不校验 GeoJSON 几何精度、不做地图渲染 | 名称核心词是 evidence+audit；与 mono-repo "trust layer" 定位一致（审计 AI 产出内容的可信度） |
| A2 | **不联网**。全部检测由纯标准库脚本离线完成：正则提取 + 内置粗粒度国家映射表 | 全局硬约束"确定性脚本优先"；也保证可复现、无网络依赖 |
| A3 | 坐标校验只做**粗粒度 bbox（外包框）**：判断坐标是否落在声称国家的经纬度外包框内。**明确声明这不是精确反地理编码**，bbox 可能包含邻国区域（如美国 bbox 含部分加拿大水域） | 离线零依赖下做精确行政边界不现实；设计里显式声明误差，符合诚实文档红线 |
| A4 | 信号类别 v0.1 收敛为 7 类：①电话区号 ②经纬度坐标 ③城市/国名 ④货币符号/代码 ⑤时区名/UTC 偏移 ⑥locale/hreflang 语言标记 ⑦地图嵌入链接（Google Maps / OSM URL 及 iframe） | 任务建议列表里的"IP 归属地引用"**移出 v0.1**（见 A5） |
| A5 | "IP 归属地引用"（如"我们的服务器位于新加坡"）v0.1 仅识别为文本声称并标 unverified，**不做 IP 库归属查询**（离线无库可查），即不产生"IP 与声称矛盾"类 finding。计划 v0.2 再评估是否内置离线 IP 段表 | 离线约束下做 IP 归属需要内置 IP→国家段表（数据量大、需外部来源），v0.1 先不做 |
| A6 | **unverified（无佐证）的地理声称也算 finding**（低严重度 info 级），因此纯 unverified 输入的退出码也是 1。用户若只想要"矛盾"可用 `--min-strength explicit` 收紧 | "证据审计"语义下，无证据支撑的声称本身就是审计对象 |
| A7 | 互证逻辑：同一文件（目录模式下同目录）内若出现与某声称**一致**的其他地理信号，则该声称升级为 inferred/explicit；完全孤立的地理声称标 unverified | "证据"字面语义：声称需要旁证 |
| A8 | 检测目标语言：中英文资产均可（国名/城市词表含中英文；电话、坐标、货币、时区、hreflang 本身语言无关）。其他语种不做承诺 | 账号资产以中英文为主；词表可扩展 |
| A9 | 输入为单文件或目录（目录递归），支持扩展名集合：md/markdown/txt/html/htm/json/csv/xml/yaml/yml；其他扩展名跳过并在报告 note 中说明 | 任务背景"单文件或目录" |
| A10 | 输出为**审计报告**（逐条 finding + 可选 JSON），不做任何改写/修复 | 审计类 skill 的统一边界 |
| A11 | CLI 语义遵循全局规范：0=干净、1=有 finding、2=用法或输入错误 | 组织硬约束 |
| A12 | "电话区号、时区、货币与国家不符"的判定基准是**国家级**映射（国家→主要区号/时区带/法定货币），不做城市级电话局向或细分时区（如美国亚利桑那不用 DST 这类例外不处理） | 粗粒度离线数据的一致性取舍；例外情形宁漏报不误报，避免噪声 |

---

## 2. 功能范围

### 2.1 信号类别与提取方式（全部离线正则/规则）

| 类别 | 提取对象 | 示例 |
|------|---------|------|
| phone | E.164 风格电话（含常见排版 `+86 21-xxxx`、`(212) 555-…`） | `+86 21 6xxx xxxx` → 国家 CN |
| coord | 经纬度坐标（十进制 + 度分格式） | `31.23°N, 121.47°E`、`31.2304, 121.4737` |
| place | 城市/国名（内置中英文词表，约 60 国 + 各 15–30 城） | "Shanghai"、"上海办公室"、"Germany" |
| currency | 货币符号与 ISO 4217 代码 | `¥`、`€`、`USD`、`CNY` |
| timezone | IANA 时区名与 UTC 偏移 | `Asia/Shanghai`、`UTC+8`、`GMT+2` |
| locale | lang 属性、hreflang、BCP47 标记 | `lang="zh-CN"`、`hreflang="de-DE"` |
| map | 地图嵌入（URL / iframe src 中的地点参数） | `google.com/maps?q=Tokyo`、`osm.org/#map=…/31.23/121.47` |

### 2.2 交叉检测规则（v0.1 共 6 条 + 1 条兜底）

| 规则 ID | 名称 | 逻辑 | 证据强度上限 |
|---------|------|------|-------------|
| R1 | phone-vs-country | 声称国 X（explicit）+ 电话属国 Y ≠ X → finding | inferred |
| R2 | tz-vs-place | 声称城市/国 + 时区或 UTC 偏移不在该国时区带内 → finding | inferred |
| R3 | currency-vs-country | 声称国 + 货币非该国法定货币 → finding（多货币并存国如欧元区成员不触发） | inferred |
| R4 | coord-vs-country | 声称国 + 坐标不在该国 bbox → finding | inferred |
| R5 | locale-vs-place | 页面声称语言/地区与 lang/hreflang 不一致 → finding | inferred |
| R6 | map-vs-place | 地图嵌入定位点与文中声称城市不一致（同国不同城报 warning 级）→ finding | inferred |
| R7 | unverified-claim | 无任何一致信号互证的地理声称 → finding（info 级，unverified） | unverified |

反例保护（不触发）：欧元区国家用 €、多时区国家（美/俄）任一时区带命中、双语城市名（中/英同指）、同文件多办公室各自信号自洽。

### 2.3 证据强度模型

| 强度 | 定义 |
|------|------|
| explicit | 信号被直接、无歧义地写出（如 `+86` 区号、完整坐标、IANA 时区名） |
| inferred | 由规则交叉推导得出（如"电话属国由区号推得"）——所有 R1–R6 的 finding 均为 inferred，报告里写明推理链 |
| unverified | 无法找到同文件/同目录内互证信号的声称（R7） |
| 未验证 | 对任何脚本无法离线核实的外部事实（如"上海确有该办公室"），skill 一律不做断言，仅报"未验证" |

> 硬约束落位：**本 skill 不做任何"声称是否为真"的联网核实**——它只审计"自洽性"。"真值核实"不在 v0.1 范围，SKILL.md 里显式声明。

---

## 3. SKILL.md 全文草案（约 180 行，< 500 行门禁内）

````markdown
---
name: geo-evidence-audit
description: Audits geographic claims in text assets (markdown, HTML, JSON, CSV) for
  internal consistency - cross-checks phone country codes, coordinates, city/country
  names, currencies, timezones, locale/hreflang tags, and map embeds against each other,
  and labels every geo claim with an evidence strength. Use when the user asks to verify,
  audit, or fact-check the geographic information of a page, site, document, or dataset;
  to find contradictions like a Shanghai office with a +1 phone number, mismatched
  timezones or currencies, coordinates outside the claimed country, or unsupported
  location claims; or to produce a JSON geo-consistency report.
---

# Geo Evidence Audit

审计文本资产中地理声称的自洽性。确定性脚本完成全部检测，离线运行，不联网。

## When to use this skill

满足以下任一场景时触发：

1. 用户要求审计/检查/验证某个页面、文档、数据集中的**地理信息是否自洽**
2. 用户怀疑存在"声称城市/国家与电话区号、时区、货币、坐标、地图嵌入不一致"的问题
3. 用户要求检查多语言页面的 hreflang / locale 标记与声称地区是否匹配
4. 用户要求找出文档中**没有佐证的地理位置声称**（unverified claims）
5. 用户要求对地理声称标注证据强度（explicit / inferred / unverified）
6. 用户要求生成地理一致性报告（文本或 JSON）
7. 用户给出含坐标的文案，要求核对坐标是否落在声称的国家范围内（粗粒度即可）
8. 用户在 CI/发布前对落地页、公司介绍、门店目录做地理信息巡检

## When NOT to use this skill

以下场景**不**触发本 skill：

1. 用户要求编写地理编码服务、地图应用等实现类任务（这是开发请求，不是审计请求）
2. 用户要求核实某个办公室**真实是否存在**（本 skill 只审计文本内部自洽性，不做真值核实，不联网）
3. 用户要求精确反地理编码（"这个坐标具体在哪个街道"）——本 skill 只有国家级粗粒度 bbox
4. 用户要求审计代码安全、供应链、API 规范等非地理主题（分别是 skill-sentry、
   skill-supply-chain-audit、api-spec-generator 的职责）

## Workflow

1. **定位资产**：确定待审计文件（单文件或目录）。目录模式下递归扫描，跳过不支持的扩展名并在报告 note 中说明。
2. **运行审计**（确定性，全部发现由脚本产生，不要靠模型现场推断地理事实）：

   ```bash
   python scripts/audit.py <path>                # 文本报告
   python scripts/audit.py <path> --format json  # JSON 报告
   ```

3. **解读 finding**：逐条向用户报告，每条含 `file:line`、信号类别、声称值、矛盾说明、证据强度与推理依据。inferred 类 finding 必须把推理链说给用户听。
4. **明确边界**：向用户说明本 skill 审计的是"自洽性"，不能证明"声称为真"；unverified 不等于虚假。

## Finding format

每条 finding 固定字段：

```
[finding] file:line  rule=R1  strength=inferred
  claimed:  "Shanghai office" (place, explicit)
  conflict: phone +1 212 555 0100 -> country US (inferred, via country calling code)
```

## Evidence strength

- **explicit**：信号被直接写出，无歧义
- **inferred**：由交叉规则推导，报告附推理链
- **unverified**：同文件/同目录内找不到互证信号的声称（info 级 finding）
- **未验证**：脚本无法离线核实的外部事实，一律如实标注，不做断言

## Boundaries and red lines

- 离线运行，绝不发起网络请求
- bbox 校验是国家级粗粒度外包框，**不是**精确反地理编码；bbox 含邻国边缘区域属预期行为
- 只报告，不修改用户文件
- 不输出任何性能数字（未实测的性能一律不写）
- 退出码：0 = 无 finding；1 = 存在 finding（含 unverified）；2 = 用法或输入错误
- 国家/城市/时区/货币映射数据的来源与证据强度见 `references/data-provenance.md`

## End-to-end example

```bash
$ python scripts/audit.py fixtures/
[finding] fixtures/phone-mismatch.md:3  rule=R1  strength=inferred
  claimed:  "Shanghai headquarters" (place, explicit)
  conflict: phone +1 (212) 555-0100 -> US (inferred, via country calling code)
[finding] fixtures/unverified-city.md:2  rule=R7  strength=unverified
  claimed:  "Zurich office" (place, explicit)
  conflict: no corroborating geo signal in same directory (unverified)
2 findings. exit code: 1
```
````

---

## 4. agents/openai.yaml 草案

```yaml
# 跨客户端兼容描述。触发场景集合必须与 SKILL.md description 等价（措辞可不同）。
name: geo-evidence-audit
version: 0.1.0
description: >
  Deterministic, offline auditor for geographic claims in text assets
  (markdown, HTML, JSON, CSV). Extracts phone country codes, coordinates,
  city/country names, currencies, timezones, locale/hreflang tags, and map
  embeds, then cross-checks them for contradictions (e.g. a claimed Shanghai
  office with a +1 phone number, a timezone inconsistent with the claimed
  city, coordinates outside the claimed country) and labels every claim with
  an evidence strength (explicit / inferred / unverified). Emits findings
  with file:line locations and an optional JSON report.
when_to_use:
  - Audit geographic consistency of a landing page, company profile, or store directory
  - Find contradictions between location claims and phone codes / timezones / currencies / coordinates / map embeds
  - Check hreflang and locale tags against claimed regions
  - List unsupported (unverified) location claims and label evidence strength
  - Produce a geo-consistency report (text or JSON)
when_not_to_use:
  - Building geocoding services or map applications
  - Verifying whether a claimed office truly exists (no network access, consistency audit only)
  - Precise reverse geocoding of coordinates (country-level bbox only)
  - Non-geo audits such as code security or supply-chain review
cli:
  entry: scripts/audit.py
  runtime: python3
  exit_codes:
    0: no findings
    1: findings present (contradictions or unverified claims)
    2: usage or input error
```

---

## 5. scripts/ 模块清单（纯标准库）

### 5.1 模块划分

| 模块 | 职责 | 关键函数签名（草案） |
|------|------|---------------------|
| `audit.py` | CLI 入口 + 编排。argparse 解析 → 收集文件 → 逐文件提取 → 汇总规则 → 渲染报告 → 决定退出码 | `main(argv: list[str]) -> int` |
| `extract.py` | 7 类信号提取（正则 + 词表匹配），输出带行号的 Signal 列表 | `extract_signals(text: str) -> list[Signal]`<br>`@dataclass Signal: category, value, line, col, strength, raw` |
| `geo_data.py` | 内置粗粒度数据：国家→区号/货币/时区带/bbox/城市词表（中英文）。纯数据模块，无逻辑 | `COUNTRIES: dict[str, CountryInfo]`<br>`@dataclass CountryInfo: iso2, calling_codes, currencies, tz_offsets, bbox, cities` |
| `rules.py` | 6 条交叉规则 + 1 条兜底规则，输入全量 Signal，输出 Finding | `run_checks(signals: list[Signal]) -> list[Finding]`<br>`check_phone_vs_country(...)`, `check_tz_vs_place(...)`, `check_currency_vs_country(...)`, `check_coord_vs_country(...)`, `check_locale_vs_place(...)`, `check_map_vs_place(...)`, `check_unverified(...)` |
| `report.py` | 文本/JSON 双格式渲染，finding 排序（文件、行号） | `render_text(findings: list[Finding]) -> str`<br>`render_json(findings: list[Finding], notes: list[str]) -> dict`<br>`@dataclass Finding: file, line, rule, strength, claimed, conflict, severity` |

依赖方向：`audit.py → {extract, rules, report} → geo_data`。禁止反向依赖，禁止互相 import。

### 5.2 CLI 参数设计

```
usage: python audit.py PATH [--format {text,json}] [--output FILE]
                            [--min-strength {explicit,inferred,unverified}]
                            [--rules R1,R2,...] [--exclude GLOB] [--quiet]

PATH                    单文件或目录（目录递归）
--format                报告格式，默认 text
--output                写入文件（缺省打 stdout）
--min-strength          过滤下限；默认 unverified（即全量报告）
--rules                 只跑指定规则，默认全部
--exclude               glob 排除（目录模式下生效，如 --exclude '*_test.*'）
--quiet                 只输出 findings 摘要行与退出码
```

行为约定：

- 无 finding 时输出 `0 findings`，退出 0；
- 目录下无任何可审计文件 → 退出 2（输入错误），报告说明原因；
- 单文件路径不存在 / 参数不合法 → 退出 2（argparse + 显式检查）。

### 5.3 退出码语义表

| 退出码 | 语义 | 触发条件 |
|--------|------|---------|
| 0 | 干净/通过 | 资产中无任何 finding（含无 unverified） |
| 1 | 有 finding | 存在 ≥1 条 finding（矛盾类或 unverified 类均算） |
| 2 | 用法或输入错误 | 参数不合法、路径不存在、无可审计文件。优先级 2 > 1 > 0 |

---

## 6. references/ 文档清单

| 文件 | 内容 |
|------|------|
| `data-provenance.md` | geo_data.py 内置数据的来源（ISO 3166 / ITU E.164 / ISO 4217 / IANA tz / bbox 粗估基准）、每类数据的 URL + 抓取日期 + 证据强度标注、更新流程。**这是硬约束"外部事实必须附 URL + 抓取日期 + 证据强度"的落点** |
| `rules.md` | 6+1 条规则的精确判定逻辑、反例保护清单（§2.2）、已知局限（bbox 误差、多时区国家、欧元区例外） |
| `evidence-model.md` | 证据强度四档定义、互证逻辑（同文件/同目录）、unverified ≠ false 的说明 |
| `scope.md` | 与相邻 skill 的分工：skill-sentry（本地运行时审计）、api-spec-generator（API 规范）、pii-signal-scanner（隐私信号）——geo-evidence-audit 只管文本资产中的地理声称自洽性 |

不创建 README / CHANGELOG / 安装指南（硬约束：这些信息进根 README）。

---

## 7. fixtures/ 清单（15 项，全部用 Write 工具逐个写）

| # | 文件 | 场景 | 预期退出码 | 预期 finding 数 |
|---|------|------|-----------|----------------|
| 1 | `consistent-office-cn.md` | 上海办公室，+86、CNY、Asia/Shanghai、CN 坐标全部自洽 | 0 | 0 |
| 2 | `consistent-office-de.html` | 柏林办公室，+49、EUR、Europe/Berlin、de-DE，HTML 格式自洽 | 0 | 0 |
| 3 | `phone-mismatch.md` | 声称上海总部，电话 `+1 (212) 555-0100` | 1 | 1（R1） |
| 4 | `timezone-mismatch.md` | 声称 London 办公室，写 `UTC+8` | 1 | 1（R2） |
| 5 | `currency-mismatch.md` | 声称 Tokyo 办公室，价格用 `€` | 1 | 1（R3） |
| 6 | `coord-outside-bbox.md` | 声称北京办公室，坐标 `48.85, 2.35`（巴黎附近，落在 CN bbox 外） | 1 | 1（R4） |
| 7 | `hreflang-mismatch.html` | `lang="zh-CN"` 但正文与 hreflang 声称 `fr-FR` | 1 | 1（R5） |
| 8 | `map-embed-mismatch.html` | 声称上海办公室，地图嵌入 `maps?q=Tokyo` | 1 | 1（R6） |
| 9 | `unverified-city.md` | "我们在 Zurich 有办公室"，全文无任何互证信号 | 1 | 1（R7, unverified） |
| 10 | `multi-contradictions.md` | 同一文件叠加 R1+R2+R3+R4 各一处 | 1 | 4 |
| 11 | `stores.json` | 门店数据，3 家自洽 + 1 家货币与国家矛盾 | 1 | 1（R3） |
| 12 | `offices.csv` | 5 行办公室数据，1 行时区与城市矛盾 | 1 | 1（R2） |
| 13 | `no-geo-claims.md` | 纯技术文档，无任何地理信号 | 0 | 0 |
| 14 | `empty.txt` | 空文件（合法输入，无事可审） | 0 | 0 |
| 15 | `e2e-mixed-dir/`（目录） | 内含 #3、#9 与一个自洽文件，端到端夹具 | 1 | 2 |

边界夹具补充（并入 #15 目录内）：`euro-member.md`（爱尔兰办公室用 € —— R3 反例保护，0 finding）、`usa-multitz.md`（纽约 + UTC-7 分部 —— R2 反例保护，0 finding）。

> 注：表中"预期 finding 数"是设计目标，实现阶段以实际运行为准校准；校准若偏离设计需在 PR 里说明原因。

---

## 8. 测试矩阵（8 触发 + 4 非触发 + 1 端到端）

### 8.1 触发测试（T1–T8）

| ID | 用户输入（示意） | 预期行为 |
|----|----------------|---------|
| T1 | "审计这篇落地页里的地理信息是否自洽" | 触发；对指定文件跑 audit.py，报告 finding |
| T2 | "检查我们多语言站点各版本的地址/电话区号是否矛盾" | 触发；目录模式 + R1/R5 |
| T3 | "验证公司介绍里声称的办公室城市与联系方式是否匹配" | 触发；R1 为主 |
| T4 | "扫描 markdown 里的坐标是否落在声称的国家范围" | 触发；R4，报告注明粗粒度 |
| T5 | "找出文档里没有来源支撑的地理位置声称" | 触发；R7 |
| T6 | "审计 JSON 数据里门店地址与货币/时区是否一致" | 触发；JSON 资产 + R2/R3 |
| T7 | "检查页面里嵌入的地图与文中声称的城市是否一致" | 触发；R6 |
| T8 | "给所有地理声称标注证据强度并输出 JSON 报告" | 触发；--format json |

### 8.2 非触发测试（N1–N4）

| ID | 用户输入（示意） | 预期行为 |
|----|----------------|---------|
| N1 | "帮我写一个地理编码服务" | 不触发（实现类请求） |
| N2 | "核实这家公司上海办公室是否真实存在" | 不触发（真值核实，非自洽性审计） |
| N3 | "审查这段代码的安全漏洞" | 不触发（skill-sentry 职责） |
| N4 | "分析这个仓库的整体结构" | 不触发（monorepo-analyzer 职责） |

### 8.3 端到端测试（E1）

对 `fixtures/e2e-mixed-dir/` 完整走一遍：运行 `python scripts/audit.py fixtures/e2e-mixed-dir/`，断言退出码 = 1、finding 数 = 2（R1 + R7 各一）、每条 finding 均含 file:line、JSON 模式可解析且字段齐全。

### 8.4 脚本级单元测试（CI 矩阵执行，与 8.1–8.3 互补）

- fixtures #1–#14 全量跑：预期退出码逐一断言（预期 exit 1 的用例一律 `if` 包裹，见 §8.5）；
- `--min-strength explicit`：对 #9 断言 0 finding、退出 0；
- `--rules R1`：对 #10 断言只出 1 条 R1 finding；
- 退出码 2：不存在路径、非法 `--format`、全不支持扩展名的目录；
- 反例保护：`euro-member.md`、`usa-multitz.md` 断言 0 finding。

### 8.5 CI 写法强制约定

```bash
# 预期 exit 1 的唯一允许写法（if 包裹 + 成功则显式失败）
if python skills/geo-evidence-audit/scripts/audit.py skills/geo-evidence-audit/fixtures/phone-mismatch.md > /dev/null; then
  echo "::error::expected exit 1, got 0"; exit 1
fi
# 注意：不允许 `|| true`（会把 exit 2 也吞成"通过"）
```

---

## 9. 硬约束核对清单（本 skill 设计 × 全局 10 条）

| 约束 | 落位 |
|------|------|
| 纯标准库零依赖，3.9+ | §5.1 模块清单全部标准库；CI py39 门禁 |
| 退出码 0/1/2 | §5.3 |
| finding 带 file:line | §2.2 / §3 Finding format / §8.3 断言 |
| 性能数字不预写 | 全文无性能声明；SKILL.md 红线显式禁止 |
| 外部事实 URL + 日期 + 证据强度 | §6 data-provenance.md |
| 目录结构四件套 | §2 SKILL.md + agents/openai.yaml + scripts/ + references/ + fixtures/ |
| SKILL.md < 500 行 | §3 约 180 行，CI 加 wc -l 门禁 |
| 确定性脚本优先 | §3 Workflow 第 2 步显式要求"不靠模型现场推断" |
| 诚实文档红线 | §2.3 未验证标注；§7 夹具预期数注明"以实际运行为准" |
| 预期 exit 1 用 if 包裹 | §8.5 |
| 夹具用 Write 工具逐个写 | §7 标注（交付纪律，实现阶段执行） |

---

## 10. 待用户确认项汇总

1. §1 解读假设 A1–A12 逐条核对（尤其是 A5 IP 归属地移出 v0.1、A6 unverified 算 finding、A12 只做国家级粗判）；
2. §7 夹具的"预期 finding 数"是否认可作为验收基线；
3. 占位 skill（#5–#10）名称与语义，待用户补充原始提示词。

确认后进入 Task #2（按本设计实现）。
