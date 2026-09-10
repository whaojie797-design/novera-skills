# Evidence model / 证据强度模型

对齐 novera-skills 前三款的四档强度口径。

## 四档定义

| 强度 | 定义 | 本款落位 |
|------|------|---------|
| explicit | 包内文件可直接验证的字面事实 | S6–S9（URL/IP/安装模式/registry 域名都在文件里逐行可查） |
| inferred | 由快照值 + 阈值约定推导 | S1–S5、S10。每条 finding 必须附：快照原始值、锚点日期、阈值及其"默认约定"标注 |
| unverified | 引用源未核实 / 时间基准降级 | contributors 端点字段细节、SARIF $schema URI、知名 skill 名清单、registry 白名单、缺 fetched_at 的本机日期锚点 |
| 未验证 | "这个包安全/可信吗"的总评 | 一律不做。无信任分、无星级、无 pass/fail 单一结论 |

## 时间锚点规则（A3）

1. 优先：快照 repo.json 的 `fetched_at`（ISO 日期/日期时间，取前 10 位解析）；
2. 回落：缺失或不可解析 → 本机当前日期，报告全局 warning 标注
   "time base is the local machine date (…), unverified"——这不是输入错误，
   退出码不受影响；
3. 一致性：最后提交/最新 release 晚于锚点 → 快照自相矛盾，警告 + 对应规则
   不判定（不硬报）。

可复现性由此保证：同一份快照在任何机器上跑出相同 finding（锚点来自快照时）；
锚点降级时结论绑定运行当日，报告已如实声明。

## 无信任分原则（A8）

- 只输出逐条 risk signal，不做加权汇总；
- finding 数量 ≠ 风险等级：2 条 low 与 1 条 high 不存在可比换算；
- 对任何信号不做恶意定性——信号只说明"与已知分发风险模式相符"或
  "与维护健康约定不符"，动机与行为判定是 skill-sentry 的领域。

## SARIF level 映射依据（A7）

- 来源：SARIF 2.1.0 OASIS Standard（verified，见 data-provenance.md）；
- 映射表：high → error、medium → warning、low / info → note（scripts/chain_rules.py
  的 SARIF_LEVEL_MAP）；
- 映射是本 skill 的呈现约定，不改变退出码语义：SARIF 输出与其他格式在
  同一输入下退出码一致；
- inventory（端点清单）与 warnings 不进 SARIF——SARIF result 只承载 finding。
