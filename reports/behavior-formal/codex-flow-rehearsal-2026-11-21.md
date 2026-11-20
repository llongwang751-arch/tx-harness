# Codex 从权限检查到判卷的真实预演

2026-11-21 · 李明远

本轮完成 1 次独立 Codex CLI 预演。00:46:44 投递新合成任务，00:47:09 记录终态，进程退出码 0。任务根据 CSV 筛出已结算交易并扣除退款。取得原件后逐项复算，本用例得 **3/3**。[运行回执](../../public/codex-flow-rehearsal-v1/observation.json) · [开跑前登记](https://github.com/llongwang751-arch/tx-harness/commit/5e9ab0f034d3eeb4861ef2ca1598fdc88241eab8) · [提示词与输入](../../supplements/codex-flow-rehearsal-v1)

| 验收项 | 实际结果 |
|---|---|
| 投递前读入 | 同一新工作区中，原生沙箱计算了提示词和 CSV 的 SHA-256，与评测端相符 |
| 投递前隔离 | 四类既有评分资产均真实存在，沙箱逐一尝试打开，四次返回 `0x80070005` |
| 原生执行 | `turn.started`、实际命令读入 CSV、成功命令写出 `outputs/summary.json`、`turn.completed` |
| 判卷 | JSON 结构 1 分、合格 ID 及原顺序 1 分、净额整数 `3035` 1 分 |

[原生访问回执](../../public/codex-flow-rehearsal-v1/access.json) · [权限命令原始输出](../../public/codex-flow-rehearsal-v1/access.stdout.jsonl) · [执行事件节选](../../public/codex-flow-rehearsal-v1/native-events.excerpts.json) · [原件](../../public/codex-flow-rehearsal-v1/summary.json) · [逐项分数](../../public/codex-flow-rehearsal-v1/score.json)

```text
python scripts/grade_codex_flow_rehearsal.py public/codex-flow-rehearsal-v1/summary.json --check
```

本次固定同一权限配置，使用实际 Codex CLI 0.169.1。服务端默认模型未独立确认。3/3 仅适用于这份合成交易题。预演已验证权限探针、投递、取证和离线复算能串起来。T03-M 正式场仍等待独立判卷抽查，正式业务运行新增 0 次。[T03-M 准入记录](codex-t03m-readiness.md)
