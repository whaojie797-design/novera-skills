# Rules / 检查项判定逻辑（E1–E12）

输入：一个 skill 包目录（必须含 SKILL.md）。
输出：Finding 列表（排序键 `file, line, rule`，同输入逐字节同输出）+ 报告头
（profile、checks run/skipped 计数）。

## profile 矩阵

| 检查项 | minimal | novera（默认） |
|--------|---------|---------------|
| E1 frontmatter-fields | 查 | 查 |
| E2 line-budget | 查 | 查 |
| E3 trigger-inventory | 只查存在性 | 存在性 + 精确 8+4+1 计数 |
| E4 exit-code-declared | 查 | 查 |
| E5 stdlib-only | 查 | 查 |
| E6 no-network-spawn | 查 | 查 |
| E7 syntax-parse | 查 | 查 |
| E8 finding-lineage | 跳过 | 查 |
| E9 fixtures-contract | 查 | 查 |
| E10 openai-yaml | 查 | 查 |
| E11 references-nonempty | 查 | 查 |
| E12 no-forbidden-files | 查 | 查 |

minimal 档 11 run / 1 skipped（E8）；novera 档 12 run / 0 skipped。
`--only` 可覆盖默认集合（`--only E8` 在 minimal 档亦可单跑）。

## E1 frontmatter-fields

- frontmatter = SKILL.md 顶部 `---` 围栏块内的 `key: value` 行；
- 必须存在；仅允许 name、description 两字段；缺字段/多字段均报
  （多字段 finding 锚定在该字段行）。
- 反例保护：无。开放标准说 name+description 是 "at minimum"，novera 档
  组织纪律收紧为"仅此两项"（见 data-provenance 的推论映射说明）。

## E2 line-budget

- SKILL.md 全文行数（splitlines 口径）≥ 500 报 finding；499 行通过。

## E3 trigger-inventory

- 存在性：`When to use` 节（标题含 "when to use"）下必须有编号列表项；
- novera 档：触发数 == 8、非触发数 == 4（标题含 "when not to use" 节下编号
  项）、端到端数 == 1（标题含 "end-to-end" 的节），**精确匹配 ±0**（lead
  裁决）；任一不符 → 汇总为 1 条 finding（不按项拆分），锚定 SKILL.md:1。

## E4 exit-code-declared

- SKILL.md 存在一行同时满足：含"退出码"或 "exit code"（大小写无关），且
  该行含数字 0、1、2 → 视为已声明。e2e 示例中的 "exit code: 0" 行不含
  1 和 2，不误触发。

## E5 stdlib-only（AST 事实检查，绝不 grep 文本）

- 遍历 `scripts/**/*.py`，AST 解析后取 Import/ImportFrom 节点；
- 顶级模块（`pkg.mod` 取 `pkg`）必须在：内置 3.9 标准库清单 ∪ 被评估包
  scripts/ 目录内的本地模块名（兄弟 .py 文件名与子目录）∪ `__future__`；
- `urllib.parse` 按顶级模块 `urllib` 判定 → 不误报；相对导入（level>0）放行；
- 注释与字符串字面量里的 `import socket` 字样绝不误报（AST 只看真实节点）。

## E6 no-network-spawn（AST Call 节点匹配）

- 命中任一即报（只报"违反结构规范"，**不对行为定性**）：
  1. Call 的点分目标属于禁用模块根（`socket` / `urllib.request` /
     `http.client` / `subprocess` / `telnetlib` / `ftplib` / `smtplib` /
     `poplib` / `imaplib` / `nntplib` / `xmlrpc.client` / `asyncio`），
     如 `socket.socket(...)`、`urllib.request.urlopen(...)`、
     `subprocess.run(...)`；
  2. `os.<func>` 且 func 匹配 system / popen / exec* / spawn* 前缀，
     如 `os.system`、`os.execv`、`os.spawnl`；
  3. `from subprocess import run` 之类把禁用模块成员绑定进本地的别名调用。
- 注意：socket/subprocess/urllib 等本身是标准库，**import 不触发 E5**，
  只有调用触发 E6（两者可同时出现在 network-call 类夹具中）。

## E7 syntax-parse

- 每个 `scripts/**/*.py` 过 `ast.parse(feature_version=(3,9))`；语法错误报
  一条 E7（锚定错误的 lineno）；该文件跳过 E5/E6（无法可靠分析）。

## E8 finding-lineage（仅 novera）

- 通过条件（任一）：SKILL.md 含 "file:line" 字样；或任一 scripts/*.py 源码
  中出现 `line` 标识符（如 dataclass 的 line 字段）；
- 否则报 1 条 finding（锚定 SKILL.md:1，issue 写明 missing）。

## E9 fixtures-contract（MANIFEST.tsv 契约，lead 裁决定稿）

- 包无 `fixtures/` 目录且 SKILL.md 未提 "fixtures" → 通过；
- 无 `fixtures/` 目录但 SKILL.md 提到 → 报（fixtures/ missing）；
- 有 `fixtures/` 目录但无 `MANIFEST.tsv` → 报 1 条（missing）；
- MANIFEST.tsv：TSV 两列 `relpath<TAB>expected_exit`，`#` 开头注释行允许；
  每条记录校验：列数恰为 2、expected_exit ∈ {0,1,2}、relpath 在包内存在
  （禁绝对路径与 `..` 逃逸）；违规各报 1 条，file:line 锚定 MANIFEST 行。
- relpath 两种基准约定均接受：以 `fixtures/` 开头的路径相对包根解析；
  其余路径相对 `fixtures/` 目录本身解析（裸夹具名）。
- 本检查**不运行**任何被评估夹具（静态边界）；expected_exit 是声明元数据。

## E10 openai-yaml

- `agents/openai.yaml` 必须存在；其首个顶层 `name:` 值必须与 SKILL.md
  frontmatter 的 name 一致（不一致报在 yaml 行）。

## E11 references-nonempty

- `references/` 必须存在且至少含 1 个文件（0 字节文件也算文件存在——"空"
  指目录内无任何文件）；缺失或为空均报（锚定 SKILL.md:1，issue 写明 missing）。

## E12 no-forbidden-files

- 包内任何文件的 basename 匹配 `readme*` / `changelog*` / `install*`
  （大小写无关，fnmatch）→ 逐文件报。目录名含 README 字样不触发（只匹配
  文件名模式）。
- 豁免：`fixtures/` 目录子树不扫描——夹具内容仅用于触发检查项，不代表宿主
  skill 语义（设计 §7）；夹具自身的完整性由 E9 的 MANIFEST.tsv 契约承担。

## 反例保护清单（不触发）

1. 注释/字符串字面量中的 import 字样（AST 口径天然免疫）；
2. `urllib.parse`（顶级模块 urllib 属标准库）；
3. SKILL.md 恰 499 行（预算 < 500 边界内）；
4. 本地兄弟模块导入（scripts 内 .py 互相 import）；
5. 目录名含 README 字样的非 README 文件；
6. 无 fixtures/ 目录且 SKILL.md 未提夹具的包（E9 通过）。
