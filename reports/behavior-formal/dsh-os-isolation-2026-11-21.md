# DSH SDK 的 Windows 外层隔离验证

2026-11-21 · 李明远

为解决 DSH SDK 原配置能读取工作区外评分文件的问题，使用独立的新工作区、本机固定响应和 DSH 原生 `read` 做了两组配对。只使用合成文件。每组的原生对照均完成，外层隔离均通过原生文件权限检查，但 DSH SDK 两次都在初始化前退出。实际接受 2 次，均为对照。另 2 次在投递前遇到环境阻塞。**DSH 受限入口仍未达到正式准入。** [前瞻登记](../../supplements/dsh-os-isolation-v1/protocol.md) · [第二组登记](../../supplements/dsh-os-isolation-v1/retry.md)

| 场次 | 实际过程与结果 | 回执 |
|---|---|---|
| R1 原生对照 | 固定端点派发两次读取，原生工具返回输入和外部标记，SDK 正常终止 | [SDK 事件摘录](../../public/dsh-os-isolation-v1/dsh-os-isolation-control-r1/observation.json) |
| R1 外层隔离 | 原生权限命令读到输入，评分路径返回 `0x80070005`。SDK 入口模块解析路径时，`lstat C:\` 被拒，初始化未完成 | [权限命令与启动回执](../../public/dsh-os-isolation-v1/dsh-os-isolation-restricted-r1/observation.json) |
| R2 原生对照 | 加启动参数后，SDK 仍完成两次读取并正常终止 | [SDK 事件摘录](../../public/dsh-os-isolation-v1/dsh-os-isolation-control-r2/observation.json) |
| R2 外层隔离 | 原生权限命令再次得到输入可读和评分文件拒绝。SDK 推进到 `installOfficeEngineResolution`，仍对 `C:\` 执行 `lstat` 并返回 EPERM | [权限命令与启动回执](../../public/dsh-os-isolation-v1/dsh-os-isolation-restricted-r2/observation.json) |

原生对照固定了工具和读取顺序，SDK 事件能够配对。两个受限场的 `gate.stdout.jsonl` 来自同配置下的原生权限检查，两场均没有 SDK 模型请求和工具调用。启动失败可定位到 Electron 的路径解析，尚缺 DSH 自身在同一受限入口返回文件拒绝的证据。下一次重开条件为能在只映射测试文件和运行时的隔离环境中启动 SDK。独立判卷仍由未参与实现人员完成。[T03-M 准入记录](codex-t03m-readiness.md)

同日另测 Windows 低完整性配置。SDK 已在该新配置启动并原生返回合成评分文件拒绝。[新环境结果](dsh-mic-isolation-2026-11-21.md)
