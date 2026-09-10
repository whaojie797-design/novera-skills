---
name: network-call
description: Minimal fixture skill package used by skill-eval-harness tests.
---

# network-call

演示用迷你 skill 包夹具，仅用于触发 skill-eval-harness 的检查项。

## When to use this skill

1. 触发场景一
2. 触发场景二
3. 触发场景三
4. 触发场景四
5. 触发场景五
6. 触发场景六
7. 触发场景七
8. 触发场景八

## When NOT to use this skill

1. 非触发场景一
2. 非触发场景二
3. 非触发场景三
4. 非触发场景四

## Workflow

1. 定位输入文件。
2. 运行脚本并解读 finding。

## Finding format

每条 finding 带 file:line 定位。

## Boundaries and red lines

- 退出码：0 = 无 finding；1 = 有 finding；2 = 用法或输入错误

## End-to-end example

```bash
$ python scripts/main.py input
0 findings.
```
