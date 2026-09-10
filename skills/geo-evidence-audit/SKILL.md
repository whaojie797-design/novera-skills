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
