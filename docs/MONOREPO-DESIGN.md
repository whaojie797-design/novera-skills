# novera-skills mono-repo 骨架设计 v1.0

> 设计人：软件架构师（高见远）
> 状态：设计稿（待用户核对 geo-evidence-audit「解读假设」后定稿）
> 范围：仓库骨架、根 README 规划、tag 与发布约定、CI 设计、10 款 skill 占位。不含任何实现代码。

---

## 1. 定位与目标

- 仓库：`whaojie797-design/novera-skills`，本地路径 `C:/github-skills/novera-skills/`。
- 品牌定位：**"Trust layer for AI agents"**。本仓库的 10 款 skill 全部围绕"对 AI 产出的内容/声明/资产做可信度审计与验证"这一主题，形成产品线而非散装工具集合。
- 交付形态：开放 Agent Skills 标准（SKILL.md + agents/openai.yaml），每款 skill 位于 `skills/<slug>/`，**按目录独立发布**（per-skill tag），后续可整体封装为跨客户端 Agent Plugin。
- 工程基调（全局硬约束，对全部 10 款 skill 生效）：
  1. 纯 Python 标准库，零第三方依赖，Python 3.9+ 兼容（CI 用 `ast.parse(feature_version=(3, 9))` 做语法门禁）；
  2. CLI 退出码：0 = 干净/通过，1 = 有 finding，2 = 用法或输入错误（优先级 2 > 1 > 0）；
  3. 每条 finding 必须带 `file:line` 定位；
  4. 性能数字实测之前一个都不许写进任何文档；
  5. 外部事实必须附 URL + 抓取日期 + 证据强度标注；
  6. skill 目录内不放 README / 安装指南 / CHANGELOG，这些进根 README 对应小节；
  7. 确定性脚本优先：能用纯脚本算出来的绝不靠 LLM 现场发挥；
  8. 诚实文档红线：不编数字、不承诺响应时间、说不出证据强度就写"未验证"；
  9. CI 中预期 exit 1 的命令必须用 `if` 包裹；
  10. 测试夹具文件一律用 Write 工具逐个写（本机 Bash 会把 `\n` 写成字面 `/n`）。

---

## 2. 完整目录树（骨架）

```
novera-skills/
├── README.md                        # 双语（英文在前），见 §3
├── LICENSE
├── .gitignore
├── .github/
│   └── workflows/
│       └── skills-ci.yml            # 单一 workflow，paths 过滤 + per-skill 矩阵，见 §6
├── docs/                            # 内部设计文档（中文），不作为发布物
│   ├── MONOREPO-DESIGN.md           # 本文档
│   └── DESIGN-geo-evidence-audit-v0.1.md
├── skills/
│   ├── geo-evidence-audit/          # 第 1 款（本次设计对象）
│   │   ├── SKILL.md
│   │   ├── agents/
│   │   │   └── openai.yaml
│   │   ├── scripts/                 # 纯标准库，入口 audit.py
│   │   ├── references/              # 数据来源与证据强度说明等
│   │   └── fixtures/                # 测试夹具，一律 Write 工具逐个写
│   ├── ai-tool-directory-publisher/ # 第 2 款（占位，仅留目录约定，实际建目录时再落盘）
│   ├── skill-eval-harness/          # 第 3 款（占位）
│   ├── skill-supply-chain-audit/    # 第 4 款（占位；差异化子集路线，与 skill-sentry 互补，管来源侧供应链画像）
│   ├── tbd-05/                      # 第 5 款（占位，名称待定，见 §5 命名规范）
│   ├── tbd-06/
│   ├── tbd-07/
│   ├── tbd-08/
│   ├── tbd-09/
│   └── tbd-10/
└── tools/
    └── py39_gate.py                 # CI 共享门禁脚本：对每个 skill 的 scripts/*.py 做
                                     #   ast.parse(compile(...), mode='exec', feature_version=(3,9)) 检查
```

说明：

- 占位 skill（第 2–10 款）**只在设计文档里占位**，不建空目录、不放空 SKILL.md——空目录进 git 无意义，且空 SKILL.md 会被客户端误读。实际动工一款、落盘一款。
- `docs/` 里的设计文档不进发布范围（发布以 skill 目录为单位打 tag），但进仓库版本管理，供后续 skill 复用规范。
- `tools/py39_gate.py` 是唯一允许的仓库级共享脚本，职责单一（3.9 语法门禁），避免每款 skill 重复实现。

---

## 3. 根 README 结构规划（双语，英文在前）

README 只放"仓库级"信息；每款 skill 的详细用法指向 `skills/<slug>/SKILL.md`，不复制。

```
# Novera Skills — Trust layer for AI agents
（中文同名标题与全文）

## What is this / 这是什么
一段话：10 款围绕 AI 产出可信度审计的 Agent Skills，
开放 Agent Skills 标准，跨客户端兼容，纯标准库实现。

## Skills / 技能列表
表格（英文节、中文节各一张）：Skill | Status | One-liner
仅列已发布的 skill，未发布的出现在下面的 Roadmap，不在 Skills 表里凑数（诚实文档红线）。

## Roadmap / 路线图（10 款 skill 路线图表格）
| # | Slug | Status | 一句话说明 | 依赖/顺序 |
| 1 | geo-evidence-audit | designed → in-dev | 审计文本资产中地理声称的自洽性 | — |
| 2 | ai-tool-directory-publisher | planned | ... | #1 完成后 |
| 3 | skill-eval-harness | planned | ... | #2 完成后 |
| 4 | skill-supply-chain-audit | planned | 来源侧供应链画像（与 skill-sentry 运行时审计互补） | #3 完成后 |
| 5–10 | tbd-* | planned | 名称与语义待定（原始提示词丢失，待用户补充） | 顺延 |

说明：#5–#10 只写占位与待定状态，不编造功能描述。

## Quick start / 快速开始
以 geo-evidence-audit 为例给出最小用法（指向 SKILL.md 触发词 + scripts/audit.py CLI）。
其余 skill 发布后在此追加小节。

## Repository layout / 仓库布局
目录树摘要（同 §2，精简版）。

## Per-skill publishing / 按目录发布
tag 约定（见 §4）、如何只拉取单个 skill 子目录、如何作为 Agent Plugin 打包（远期，标注 planned）。

## Constraints / 工程约束
零依赖、Python 3.9+、退出码语义、finding 带 file:line、无性能承诺（引用硬约束清单）。

## License
```

双语规则：英文节在前、中文节在后，两节内容一一对应；版本号、slug、命令、退出码等专有内容两节一致。

---

## 4. per-skill tag 约定

- 格式：`<slug>-v<semver>`，例如 `geo-evidence-audit-v0.1.0`。全仓库唯一命名空间，tag 名自带 slug，避免 mono-repo 下多 skill 版本号混淆。
- 语义化版本：MAJOR = 破坏性变更（SKILL.md 触发语义/CLI 参数/输出结构不兼容）；MINOR = 新增信号类别、新增 finding 规则、新增报告字段；PATCH = 修复误报/漏报、文档与夹具修正。
- tag 打在包含该 skill 变更的 commit 上；打 tag 前该 skill 的 CI 矩阵必须全绿。
- tag 与目录一一对应：看到 `skill-supply-chain-audit-v0.1.0` 即知只涉及 `skills/skill-supply-chain-audit/`。允许一个 commit 同时推进两个 skill 并打两个 tag（如公共 `tools/` 变更带动），tag message 里注明。
- 禁止裸版本 tag（如 `v0.1.0`）和 `latest` 浮动 tag。

---

## 5. 后续 9 款 skill 的占位与命名规范

### 5.1 命名规范

1. slug 全小写 kebab-case，`[a-z][a-z0-9-]*`，长度 ≤ 32；
2. 语义模式：`<对象>-<动作>` 或 `<对象>-<性质>`，如 `geo-evidence-audit`（对象=geo-evidence，动作=audit）、`skill-eval-harness`（对象=skill，动作=eval）；
3. 禁止品牌词（novera）出现在 slug 里（仓库名已表达）；禁止版本号、日期进 slug；
4. 名称需能从字面推出输入对象与审计动作，否则视为不合格命名；
5. slug 一旦打首个 tag 即冻结，重命名视为 MAJOR 变更（保留旧 tag + 新 tag 双轨一个 MINOR 周期）。

### 5.2 占位状态

| # | slug | 已知信息 | 状态 |
|---|------|---------|------|
| 2 | ai-tool-directory-publisher | 开发顺序 #2 | 名称确认，语义待用户核对（占位） |
| 3 | skill-eval-harness | 开发顺序 #3 | 名称确认，语义待用户核对（占位） |
| 4 | skill-supply-chain-audit | 开发顺序 #4；**差异化子集路线**：只管"来源侧供应链画像"，与已发布 skill-sentry v0.2.0 的"本地运行时审计"互补，不重叠 | 名称与路线确认（占位） |
| 5–10 | tbd-05 … tbd-10 | 原始提示词丢失，名称与语义均待定 | 占位，等用户补充 |

纪律：占位条目一律写"待定/待核对"，**不基于 slug 猜测编造功能描述**（与 geo-evidence-audit 的「解读假设」机制一致：动工前先出解读假设，用户核对后再出设计）。

---

## 6. CI 设计（.github/workflows/skills-ci.yml）

单 workflow，两层过滤 + 一个矩阵：

```yaml
# 设计要点（非完整可运行文件，实现阶段照此落盘）
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }

jobs:
  changes:                 # job 1：paths 过滤，输出本次变更涉及的 skill 列表
    # 用 dorny/paths-filter 或 git diff --name-only 按 skills/<slug>/ 前缀分组；
    # tools/ 或根文件变更 → 触发全部已存在 skill 的矩阵。

  test-matrix:             # job 2：needs: changes，strategy.matrix.skill = 变更列表
    strategy:
      fail-fast: false     # 单个 skill 挂不影响并行观察其他 skill
      matrix:
        skill: ${{ fromJSON(needs.changes.outputs.skills) }}
    steps:
      - checkout
      - py39 门禁: python tools/py39_gate.py skills/${{ matrix.skill }}/scripts
      - 全量测试: 期望 exit 0 的用例直接跑
      - 预期失败用例: 必须用 if 包裹，见下
```

### 6.1 「预期 exit 1 必须用 if 包裹」

本仓库大量测试用例的语义就是"给脏数据 → 期望 exit 1"。在 `set -e` 语义下（GitHub Actions bash shell 默认 `set -e`）直接执行会中止后续步骤——历史上该陷阱踩过 3 次，强制约定写法：

```bash
# 正确（唯一的允许写法）
if python skills/geo-evidence-audit/scripts/audit.py skills/geo-evidence-audit/fixtures/phone-mismatch.md; then
  echo "::error::expected exit 1, got 0"; exit 1
else
  echo "got expected non-zero exit"
fi

# 错误（禁止）
python .../audit.py .../phone-mismatch.md          # set -e 下直接中止
python .../audit.py .../phone-mismatch.md || true  # 吞掉退出码，exit 2 也会"通过"，等于没测
```

即：**if 包裹 + 命令成功则显式报错失败**，不允许 `|| true` 式吞码。

### 6.2 矩阵内容（对每个 skill 执行）

1. `py39_gate`：3.9 语法兼容门禁；
2. `stdlib-zero-dep` 门禁：grep 校验 scripts/ 无 `import` 第三方模块名（维护白名单 = 标准库模块清单）；
3. 单元测试：fixtures 全量跑一遍（含 §6.1 的预期失败用例）；
4. 触发词冒烟：SKILL.md 声明的 8 触发 + 4 非触发 + 1 端到端用例的脚本层可执行部分。

### 6.3 发布前置检查

打 tag 前 CI 必须满足：该 skill 矩阵全绿 + SKILL.md < 500 行（CI 加一行 wc -l 门禁）+ 根 README 的 Roadmap 表状态已同步。

---

## 7. 跨客户端兼容与远期 Plugin 封装

- 每个 skill 必须同时有 `SKILL.md`（Agent Skills 标准，frontmatter 仅 name + description）与 `agents/openai.yaml`（OpenAI 系客户端描述），两者语义一致，`description` 内容允许措辞差异但触发场景集合必须等价。
- 远期封装为 Agent Plugin：预计形态 = 仓库根新增 `plugin/manifest` 类聚合文件 + 按 skill 目录组装。本文档只预留该演进方向，**不做具体设计**（避免为未定需求过度设计）。

---

## 8. 与既有四个独立仓库的关系

- `C:/github-skills/` 下已发布：skill-sentry、monorepo-analyzer、api-spec-generator、pii-signal-scanner（各自独立仓库）。
- novera-skills 是新产品线，**不迁移**上述仓库；skill-supply-chain-audit 通过"来源侧 vs 运行时"分工与 skill-sentry 互补，设计时需在 SKILL.md 边界一节显式声明两者分工，避免触发场景重叠。
- 后续若出现功能重叠候选 skill，先写差异化子集说明（同 #4 模式）再动工。

---

## 9. 验收清单（本设计的 DoD）

- [x] 目录树覆盖 10 款 skill 占位与共享 tools/
- [x] 根 README 双语结构 + 10 款路线图表格规划（#5–#10 如实标注待定）
- [x] per-skill tag 约定可操作
- [x] CI 含 paths 过滤、per-skill 矩阵、if 包裹约定、py39 门禁、wc -l 门禁
- [x] 全部 10 条硬约束在 §1 逐条落位
- [ ] 用户核对 DESIGN-geo-evidence-audit-v0.1.md 的「解读假设」→ 定稿
