# 固定响应工具契约现场

2026-10-24，李明远。两款真实官方Harness串行执行；没有神经模型推理。先校准，再按[已冻结正式协议](../../../supplements/controlled-adapter-v1/protocol.md)执行四臂。见[报告](../../../reports/controlled-adapter-v1.md)、[逐项复算](../../../reports/controlled-adapter-v1.json)。

| 包 | 阶段 | 是否接受任务 | 结果 |
|---|---|---|---|
| [CA00-codex-calibration](CA00-codex-calibration/manifest.json) | 校准 | 否 | 配置序列化拒绝，启动尝试保留，不算独立任务 |
| [CA00-dsh-calibration](CA00-dsh-calibration/manifest.json) | 校准 | 是 | 通过 |
| [CA01-codex-calibration](CA01-codex-calibration/manifest.json) | 校准 | 否 | 不支持的字段，启动尝试保留，不算独立任务 |
| [CA02-codex-calibration](CA02-codex-calibration/manifest.json) | 校准 | 是 | 审批未放行固定工具，适配器未知，保留在分母 |
| [CA03-codex-calibration](CA03-codex-calibration/manifest.json) | 校准 | 是 | 显式预批唯一工具后通过 |
| [CA11-dsh-error](CA11-dsh-error/manifest.json) | 正式 | 是 | 预期错误回包通过 |
| [CA12-codex-success](CA12-codex-success/manifest.json) | 正式 | 是 | 125字节原件和回包通过 |
| [CA13-dsh-success](CA13-dsh-success/manifest.json) | 正式 | 是 | 125字节原件和回包通过 |
| [CA14-codex-error](CA14-codex-error/manifest.json) | 正式 | 是 | 预期错误回包通过 |

九份包包含七次实际接受任务；校准五次尝试中三次接受、两次通过、一次未知，正式四次均通过。两次配置拒绝不计产品任务。每包manifest绑定其余所有文件，原件按字节保留；缺失日志为空文件并如实判定，不用示例填补。

原始execution中旧适配器曾把stdin写入记actual_submitted。公开投影明确区分actual_submission_attempt与由原生turn_start证明的task_accepted；两次配置拒绝的actual_submitted已按后者纠正，并保留原execution摘要及错误。没有把未进入任务的启动算运行。

两款普通事件都未独立暴露isError布尔；实际MCP的isError、原生status、端点回包分别保留。Codex原生item_id不冒充model call_id。环境值、系统/Skill正文、原始SDK wire不公开。可信MCP写文件不测沙箱，固定响应不测真实模型任务质量，不外推五产品共同控制。
