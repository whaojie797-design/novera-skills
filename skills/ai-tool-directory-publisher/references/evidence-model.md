# Evidence Model / 证据强度模型

本 skill 对 listing 材料校验、跨目录一致性、提交状态三类检查标注证据强度。

| 强度 | 定义 | 来源规则 |
|------|------|---------|
| **explicit** | 对照单条规则直接得出 | V1–V5（verified 快照）、S1 |
| **inferred** | 由跨文件对比推导，finding 必须附两侧 file:line 与字段值 | C1 |
| **unverified** | 快照未经官网核实的条目（verified=false 的目录快照）。默认**不跑**，需 `--include-unverified` 显式开启，开启后 finding 强度标 unverified | V1–V5（unverified 快照） |
| **未验证** | 任何关于"该工具是否会被目录站收录"的判断。skill 一律不做断言 | — |

## 快照 verified 标志与 --include-unverified 的关系

- `DirectorySpec.verified=true`（4 家）：实现期已访问官方提交页并记录其要求
  （见 data-provenance.md 逐站核实表），默认参与校验；
- `DirectorySpec.verified=false`（2 家：ai-tools-directory、aitools-fyi）：
  官方渠道无法核实要求，快照为合理归纳，默认跳过；`--include-unverified`
  开启后参与校验，finding 标注 unverified；
- **注意**：即使 verified=true，官方页面也未公布字符级限制数字——快照中的
  长度区间/枚举/截图规格是编制基线（证据强度 unverified，见 data-provenance），
  一切以官网为准。

## "材料全绿 ≠ 收录"（红线条目）

本 skill 校验的是**材料的完整性与自洽性**，不预测也不承诺目录站的收录结果：

- 全部字段合规、四锚点一致、状态表合法，只说明材料"可提交"；
- 是否收录由各目录站的编辑审核决定（4 家 verified 站点均为付费 + 编辑审核
  模式，且明确"未通过退款"，审核通过率无公开数据——一律不做断言）；
- 向用户解读结果时必须明确这一边界。

## 与 CLI 选项的关系

- `validate` 默认：4 家 verified 快照逐个跑（无 slug 线索的 listing 对全部
  verified 快照各跑一遍，相同 finding 去重）；
- `--directory SLUG`：只跑指定快照（slug 必须存在于快照，否则退出码 2）；
- `--include-unverified`：追加 2 家 unverified 快照，finding 标 unverified；
- 退出码语义与全局一致：0 无 finding；1 有 finding（含 unverified）；2 用法
  或输入错误，优先级 2 > 1 > 0。
