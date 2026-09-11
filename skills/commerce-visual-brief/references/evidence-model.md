# Evidence model - commerce-visual-brief

## 证据强度四档

| 强度 | 定义 | 使用者 |
|------|------|--------|
| explicit | 包内字面事实：brief 文本中的直接声明、词表命中 | V1、V6–V10 |
| inferred | 跨字段/跨节推导，finding 附两侧值与推理链 | V2–V5 |
| unverified | 平台快照未核实条目；或 default_convention 约定表 | 平台条目（默认不跑）、映射表标注 |
| 未验证 | 一律不做断言的对象 | —— |

## 快照 verified 标志与 --include-unverified 的关系

- `verified=true`：实现阶段官方页直接抓取成功、数值逐字读自原文
  （当前仅 amazon，见 data-provenance.md）。这只代表"快照时刻页面这么写"，
  **不代表数值永久现行**——快照会过期，平台规范为准。
- `verified=false`：核实不到官方原文（仅百科/第三方/业务线错位），数值
  全部留空。默认不参与 V6–V9（静默跳过，报告头部说明）。
- `--include-unverified` 显式开启后：unverified 平台上的规格声明逐条出
  strength=unverified 的 finding，value 写明"快照未核实、无法校验"。
  这是**诚实标注**，不是编造数字补位。
- 反过来，verified 快照给出的每条 V6–V9 finding 的 expected 都附
  source_url 与 snapshot_date，便于用户回源核对。

## 诚实红线（两句话，报告与人工解读都必须遵守）

1. **词表命中 ≠ 违法**：V10 极限词命中只是字面风险提示，不是广告法或平台
   规则的违法定性；每条 finding 的 expected 恒带免责声明。
2. **材料全绿 ≠ 审核通过 ≠ 转化保证**：validate 退出码 0 只说明
   "本 skill 的检查范围内未发现字面问题"；广告审核结果、图片拍摄质量、
   商品转化效果均不在本 skill 的可断言范围内，一律不做预测。

## default_convention 约定的诚实标注

REQUIRED_FIELDS / CATEGORY_DECLS / CATEGORY_SCENE_CONFLICTS /
CURRENCY_LOCALE / 白底与冲突词表均为起草约定（default_convention）。
相关 finding 的 expected 逐条标注 "… is a default convention …, not a
fact"；用户可按自己的品类与平台要求调整词表（改 brief_data.py 即可，
校验逻辑不变）。
