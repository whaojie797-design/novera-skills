---
name: minimal-ok
description: Minimal fixture skill package used by skill-eval-harness tests.
---

# minimal-ok

演示用迷你 skill 包夹具：只有触发清单，无 8+4+1 结构。

## When to use this skill

1. 触发场景一
2. 触发场景二
3. 触发场景三

## Workflow

1. 定位输入文件。
2. 运行脚本并解读 finding。

## Finding format

每条 finding 带 file:line 定位。

## Boundaries and red lines

- 退出码：0 = 无 finding；1 = 有 finding；2 = 用法或输入错误
