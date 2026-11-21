# Codex × T03-M 正式实测准备

2026-11-19。按 [Week 5 反馈](https://github.com/llongwang751-arch/tx-harness/issues/3)选 Codex 做首场，沿用冻结的 T03-M。权限已验证，正式场等待独立判卷抽查。

| 验收项 | 实际观察 |
| --- | --- |
| 允许读入 | Codex CLI 0.169.1 的真实命令工具计算了 5 份输入及提示词的 SHA-256，与评测端清单逐件一致 |
| 拒绝访问 | 同一 CLI 的原生 Windows 沙箱使用与任务一致的权限配置。评测端先验证四份文件存在且可读。沙箱内逐个打开评分器、评分细则、标准答案和参考产物，四次均返回 Windows `0x80070005` |
| 业务任务 | 只提交权限诊断。T03-M 正式题面未作为业务任务发送，结果目录为空，正式运行和分数均为 0 条 |
| 独立判卷 | 新版规则已获独立确认。旧版收到独立复算，判断前已看过标准答案，盲判仍待收回。[复核回执](review/T03-M-independent-rule-review-2026-11-21.md) |

来源在[复核回执](../../public/behavior-formal/codex-t03m-access.json)和[原生沙箱输出](../../public/behavior-formal/codex-t03m-sandbox.stdout.jsonl)。负向检查由原生沙箱的确定性命令执行。第一次尝试让模型执行检查时，模型拒绝访问受限位置，未调用工具；该回合本身不算系统拒绝证据。第二次模型回合只核对允许读取的文件，已观察到成功的命令结果。两次均为权限诊断，按发生顺序保留。结论限于记录的 Windows 权限配置与四个绝对路径，其他执行方式和产品另行验证。

其他四款的实际文件权限诊断已单独归档。[五款权限准入核对](surface-access-2026-11-19.md)

2026-11-21 用相同权限配置跑通一次合成交易题预演，原生完成并审计为 3/3。[独立预演记录](codex-flow-rehearsal-2026-11-21.md)

收到 Codex 辅助复核后，按提交复算确认 C01 的题面与精确字符串判定存在分歧。已准备题面补充候选，正式场暂缓，等待独立判卷及对候选口径的确认。[辅助复核记录](review/T03-M-assisted-2026-11-21.md) · [候选条款](../../supplements/t03m-prompt-review-v1/amendment.md)

2026-11-21 已备齐新版题面和 8 个正反例，固定判卷器复算全部符合预期。[新版审阅材料](../../supplements/t03m-prompt-review-v1/README.md)

新版先收到一份署名 Codex 的辅助复核，之后收到未参与判卷器实现的技术复核人确认。C01、C06 新版规则已冻结。旧版 C01 异议继续保留，待另收盲判后准备新版正式运行登记。[冻结记录](../../supplements/t03m-prompt-review-v1/freeze.md) · [新版辅助复核回执](review/T03-M-draft-assisted-2026-11-21.md)

## 第一场如何开跑

以下命令对应旧题面前瞻登记 `product_default-codex-T03-M-r2`，保留作历史准入参考。新版使用单独的运行 ID 和登记。旧登记使用干净 CLI 的服务默认模型，后端身份没有独立确认。[旧版前瞻登记](../../supplements/behavior-protocol-v3/run-register.json)

启动器先校验 Git 冻结和独立复核记录，再创建新工作区。正式任务将使用该目录的实际字节重跑原生权限检查，顺序成功才会提交。

```powershell
python -B -X utf8 scripts/behavior_preflight.py --check-formal-readiness
python -B -X utf8 scripts/run_codex_pilot.py --track product_default --case T03-M --replicate 2 --registration-commit 93fe268f6c5b16c6431e66211885376351e0da42 --execute
```

复核人先按[操作单](../week6/judge-spot-check.md)盲判 C01、C06，再复算。记录复核日期、身份关系、Git 提交、命令、每项观察、理由及是否同意按冻结口径运行。复核意见由操作者归档，实施者不能代签。若复核对判分口径有实质异议，先修订和重新冻结协议。正式场产物分按 60 分制记录，模型演绎过程和五款因果排名不由这项测试给出。
