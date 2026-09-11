# Rules - commerce-visual-brief

V1–V10 逐条判定逻辑。全部为字面/词表级判定，零语义理解，零网络，零图片读取。

## 完整性组

### V1 missing-required-field（explicit）

必填字段四项：`product_name` / `pricing` / `size_chart` / `color_card`
（brief_data.py REQUIRED_FIELDS，**default_convention**）。缺任一项在
`文件:1` 报一条，field=缺失字段名，value=(missing)。
required 集是起草约定，不是事实；品类专属合规声明由 V2 管，不在此重复报。

### V2 missing-category-declaration（inferred）

brief 的 category/品类 字段命中 CATEGORY_DECLS 词表键（化妆品/护肤品/食品/
保健品/母婴/电器，**default_convention**）时，检查全文是否包含该品类必需
声明关键词（如 化妆品→成分+备案）；报第一个缺失关键词，每品类至多 1 条。
声明可以以键（`成分: 玻尿酸`）或值（正文提到"备案"）两种形式存在。
品类词不在映射表 → 不报（宁漏报不误报）。

## 一致性组

### V3 pricing-locale-mismatch（inferred）

brief 同时声明价格字段（pricing/price/价格/售价/定价）与 locale 字段
（locale/语言/lang）时，校验价格中的币种 token（$ ¥ € £ / CNY USD JPY 等）
是否在该 locale 的允许集内（CURRENCY_LOCALE，**default_convention**）。
`¥` 为 CNY 与 JPY 共享字形，两个 locale 均接受。locale 不在表内 → 不判定
（保持沉默）。只报一侧：价格行。

### V4 claim-evidence-gap（inferred）

只查"声称引用了图位但清单缺失"：卖点文本含 `图N` 字样而 placement 清单
（`图N:`）中无对应编号 → 报声称所在行。卖点未引用任何图位 → 不报
（不要求全部卖点配图）。

### V5 category-scene-mismatch（inferred）

品类字段与场景文本（scene/场景 字段，或含"场景/模特"的卖点）命中
CATEGORY_SCENE_CONFLICTS 冲突对（母婴×酒吧/夜店/夜场/酗酒/赌、
医疗器械×酒吧/夜店/派对、食品×有毒/腐坏，**default_convention**）→ 报
场景行。场景词不在映射表内 → 不硬报，宁漏报不误报。

## 图片规格组（V6–V9，仅 verified 平台快照参与）

仅当 `--platform SLUG` 指定平台时运行；缺省时整组跳过（报告头部有说明）。
unverified 平台默认跳过；`--include-unverified` 开启后对其上的规格声明出
strength=unverified 的"未核实、无法校验"标注（V6），不产出数值结论。
规格声明只认提及 主图/图片/图位/规格/照片/image/photo/img 的行，防止把
随机数字误读成规格。声明行带其他平台标记（如 `[淘宝]`）而校验目标不同 →
跳过该行（声明指向别的平台）。快照来源与核实状态见 data-provenance.md。

### V6 image-spec-format（explicit）

声明格式不在快照允许集内（如 amazon 快照允许 jpg/jpeg/tif/tiff/png/gif，
声明 webp → 报）。

### V7 image-spec-dimension（explicit）

声明尺寸超出快照区间（amazon：最长边 500–10000 px，低于下限或高于上限 →
报，附具体越界侧）。

### V8 main-image-count（explicit）

声明张数超出快照区间。amazon 快照为"至少 1 张、无上限"（(1, None)），
bound 文案为 ">= 1"；声明 0 张 → 报。

### V9 image-whitespace-missing（explicit）

快照要求主图白底（amazon：纯白 RGB(255,255,255)）而声明明确非白底
（非白底/灰/黑/彩色/渐变/场景图等词，**default_convention** 词表）→ 报。
声明白底或沉默 → 不报。

## 合规提示组

### V10 extreme-word-risk（explicit + 免责声明）

EXTREME_WORDS 词表（8 模式，中文为主英文为辅）逐行匹配 fields/claims/
placements/image_specs 文本；每行至多 1 条；expected 恒含免责声明原文：
"lexicon hit is a risk hint, not a legal determination; check platform
rules and applicable law"。
反例保护：含比较保护词（更耐用/较上一代/相比/较之/比上一代/提升/
more durable/compared to/improved）的行跳过；"最X"模式要求强度字真实存在
（"最近上新"不命中）。
**词表命中 ≠ 违法**——本 skill 不做任何法律定性。

## 输出分离规则

- **inventory（清单）≠ 风险**：inventory 子命令输出图位与规格声明全量清单，
  纯信息性，退出码恒为 0（输入错误除外），永远不影响 validate 的退出码。
  图位是否符合拍摄意图由设计侧判断，本 skill 不做评判。
- finding 排序：(file, line, rule) 字典序，输出确定性（同输入逐字节相同）。
- 退出码：0 = 无 finding；1 = 至少 1 条 finding；2 = 用法/输入错误
  （无子命令、未知子命令、非法 --platform slug、路径不存在、无 brief 结构）。
  优先级 2 > 1 > 0。
