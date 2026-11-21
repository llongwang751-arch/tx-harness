# 商户结算对账与实际判卷资产隔离

2026-11-21 · 李明远

本次把权限验证接到了一次实际对账任务。先登记 11 笔合成订单、5 类排除规则及三份约定产物，同时锁定实际评分器、细则、Oracle、参考结果四份资产的 SHA-256。评测端逐件读取，正向探针核对三份输入及提示词，负向探针逐个打开实际评分文件。Codex 在隔离通过后提交，正常结束并交付三份原件，固定判卷为 **100/100**。[初始登记](https://github.com/llongwang751-arch/tx-harness/commit/c8fac9ccd9c1687879efa5cda3b01a2a83c36764) · [成功场前瞻登记](https://github.com/llongwang751-arch/tx-harness/commit/581c9397a620f347888c6184f7c447a08f7ad65a) · [输入、规则和哈希](../../supplements/dsh-settlement-v1)

| 运行 | 投递情况 | 观察与裁定 |
|---|---|---|
| DSH SDK Low | 接受后鉴权失败 | 两个工作区角色通过检查，参与方进程核对四份输入哈希，实际评分文件四次均为 Win32 5。SDK 终态为 `ACCOUNT_SIGN_IN_REQUIRED`，无产物，未计业务分。[权限和终态](../../public/settlement-20261121/dsh-settlement-20261121-r1/observation.json) |
| Codex 第一次 | 投递前停止 | PowerShell 探针的哈希表语法错误。记录为准备故障。[现场](../../public/settlement-20261121/codex-settlement-20261121-r1/observation.json) |
| Codex 第二次 | 投递前停止 | 探针核对到全部输入，也实测原临时目录下四份评分文件可读，启动器拦截。[原生命令回执](../../public/settlement-20261121/codex-settlement-20261121-r2/access.stdout.jsonl) |
| Codex 第三次 | 接受并完成 | 将同一批评分文件移到明确禁止访问的评测树，哈希一致。四个评分路径实际打开均返回 `0x80070005`，随后投递。一次命令执行退出 1，后续命令恢复并写出三份交付。原始输入哈希与投递前一致。[隔离回执](../../public/settlement-20261121/codex-settlement-20261121-r3/access.json) · [原生工具记录](../../public/settlement-20261121/codex-settlement-20261121-r3/native-events.excerpts.json) · [三份原件](../../public/settlement-20261121/codex-settlement-20261121-r3/outputs) |

共接受业务任务 2 次，其中 Codex 有效完成 1 次，DSH 的 1 次因账户握手失败无可判产物。两个 Codex 投递前停止单列。标准 DSH SDK 启动曾做零投递排查，Low 进程写共享 SDK 运行配置时返回 `EPERM`。本场证据支持实际评分资产在两种已测权限配置下的可达性判断。两端的模型、Skill 和登录配置有差别，且 DSH 缺可判结果，比较仅限各自观察到的故障和产物。

## 判卷与复核

合格订单标识、逐笔金额、排除原因优先级、汇总、汇总与原始明细对账五项全过。原件包含 5 笔入账、6 笔排除，手续费 655 分，实付 41140 分。本案实际使用的判卷资产在任务结束并收集原件后公开，全部可以复算 SHA-256。把同时满足多项排除条件的 O-703 改为较低优先级的原因，复算为 80/100。把手续费汇总从整数改成等值字符串，复算为 65/100。[逐项判卷](../../public/settlement-20261121/codex-settlement-20261121-r3/score.json) · [跑后公开的评分器及参考](../../public/settlement-20261121/grader-assets)

```text
python scripts/audit_settlement_evidence.py
```

本案登记为工程实测。T03-M 正式场等待独立判卷。[正式场状态](codex-t03m-readiness.md)
