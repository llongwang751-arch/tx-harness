# Codex 新版 T03-M 正式实测

2026-11-21 21:05–21:06（北京时间），按预登记投递新版首场 `product_default-codex-T03-M-r3`。Codex CLI `0.171.0-alpha.13` 约 54.8 秒后正常退出。九份交付齐全，固定判卷 **60/60**，十项产物检查及适用的 CSV 严格解析检查全部通过，`accepted=true`。[预登记](../../supplements/t03m-prompt-review-v1/formal-run-registration.json) · [现场回执](../../public/behavior-formal/product_default-codex-T03-M-r3/observation.json) · [逐项得分](../../public/behavior-formal/product_default-codex-T03-M-r3/score.json)

## 判卷复核

旧版采用两阶段复核。独立同学先收到题面和三份实际产物，按题面判 C01 通过、C06 不通过，随后运行旧判卷，复算两项均失败、42/60。项目负责人转述复核人未参与实现，作出判断前未看过参考答案或机器判分。复核人保留旧版 C01 异议、同意 C06 扣分。归档按匿名同学记录，复核人原始环境和确切命令未随回执提供。维护侧用固定快照复演，确认 42/60。新版规则由另一位独立技术复核人确认，明确 C01 的 `reason` 精确字符串要求，并保留 C06 的公告字节要求。旧版历史成绩与异议保留。[旧版盲判及复算](review/T03-M-old-blind-2026-11-21.json) · [新版规则冻结](../../supplements/t03m-prompt-review-v1/freeze.md)

## 本场证据与结论

| 判断 | 可复核依据 |
|---|---|
| 正式任务满足权限准入，置信度高 | 在实际工作区用同一 Codex 原生权限配置核对 5 份输入和新版题面。评测端按哈希确认四份评分资产存在，参试侧逐一打开均返回 Windows `0x80070005`。探针完成后才投递，输入哈希在任务后仍相同。结论覆盖本场配置下这四个目标。[原生访问输出](../../public/behavior-formal/product_default-codex-T03-M-r3/access.stdout.jsonl) · [权限回执](../../public/behavior-formal/product_default-codex-T03-M-r3/access.json) |
| Codex 有一次工具错误并完成交付，置信度高 | 先用 PowerShell 读五份输入，再尝试运行 `python --version`，收到命令不可用错误。随后的 PowerShell 命令依次写入步骤文件和最终交付。工具终态显示 `turn.completed`，原始会话日志留在评测端，公开事件节选保留工具命令及退出码。[工具事件节选](../../public/behavior-formal/product_default-codex-T03-M-r3/task-events.excerpts.json) |
| 两项争议检查在本场都通过，置信度高 | C01 排除 P-B 并逐字写入 `draft_do_not_apply`。C06 交付公告只替换发布时刻，保留标签和其余字节。按冻结的 `a6bb1d2` 判卷器运行，十项权重 100/100。发布原件、规则版本及完整评分回执，可逐件复算。[九份原件](../../public/behavior-formal/product_default-codex-T03-M-r3/outputs) · [提交给产品的完整文本](../../public/behavior-formal/product_default-codex-T03-M-r3/submitted-prompt.md) |

本场记录的是指定 Codex CLI 配置的单次产物表现。与历史场相比，题面和运行环境存在差异。默认后端身份及服务侧内置 Skill 状态未知，仅凭 42 和 60 两个分数无法估计题面改动的独立效果。

```bash
python -B -X utf8 scripts/audit_t03m_revised_run.py
```
