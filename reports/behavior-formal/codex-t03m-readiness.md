# Codex × T03-M 正式实测准备

2026-11-19。按 [Week 5 反馈](https://github.com/llongwang751-arch/tx-harness/issues/3)选 Codex 做首场，沿用冻结的 T03-M。权限已验证，正式场等待独立判卷抽查。

| 验收项 | 实际观察 |
| --- | --- |
| 允许读入 | Codex CLI 0.169.1 的真实命令工具计算了 5 份输入及提示词的 SHA-256，与评测端清单逐件一致 |
| 拒绝访问 | 同一 CLI 的原生 Windows 沙箱使用与任务一致的权限配置。评测端先验证四份文件存在且可读。沙箱内逐个打开评分器、评分细则、标准答案和参考产物，四次均返回 Windows `0x80070005` |
| 业务任务 | 只提交权限诊断。T03-M 正式题面未作为业务任务发送，结果目录为空，正式运行和分数均为 0 条 |
| 独立判卷 | [两项抽查操作单](../week6/judge-spot-check.md)已就绪，目前没有收到未参与实现者的记录 |

来源在[复核回执](../../public/behavior-formal/codex-t03m-access.json)和[原生沙箱输出](../../public/behavior-formal/codex-t03m-sandbox.stdout.jsonl)。负向检查由原生沙箱的确定性命令执行。第一次尝试让模型执行检查时，模型拒绝访问受限位置，未调用工具；该回合本身不算系统拒绝证据。第二次模型回合只核对允许读取的文件，已观察到成功的命令结果。两次均为权限诊断，按发生顺序保留。结论限于记录的 Windows 权限配置与四个绝对路径，其他执行方式和产品另行验证。

其他四款的实际文件权限诊断已单独归档。当前仍未收到独立判卷回执，T03-M 暂留待运行。[五款权限准入核对](surface-access-2026-11-19.md)

## 第一场如何开跑

[前瞻登记](../../supplements/behavior-protocol-v3/run-register.json)固定新 ID `product_default-codex-T03-M-r2`、题面、判卷配置、接入二进制摘要、单次尝试和 1200 秒预算。计划使用干净 CLI 的服务默认模型，后端身份没有独立确认。其他产品不在本次登记范围内。

启动器先校验 Git 冻结和独立复核记录，再创建新工作区。正式任务将使用该目录的实际字节重跑原生权限检查，顺序成功才会提交。

```powershell
python -B -X utf8 scripts/behavior_preflight.py --check-formal-readiness
python -B -X utf8 scripts/run_codex_pilot.py --track product_default --case T03-M --replicate 2 --registration-commit 93fe268f6c5b16c6431e66211885376351e0da42 --execute
```

复核人先按[操作单](../week6/judge-spot-check.md)盲判 C01、C06，再复算。记录复核日期、身份关系、Git 提交、命令、每项观察、理由及是否同意按冻结口径运行。复核意见由操作者归档，实施者不能代签。若复核对判分口径有实质异议，先修订和重新冻结协议。正式场产物分按 60 分制记录，模型演绎过程和五款因果排名不由这项测试给出。
