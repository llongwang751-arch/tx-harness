# DSH 原生文件工具与 Shell 的单次对照

2026-11-19 · 李明远

文件收发场中，DSH 原件已交付，补做的 Shell 校验却返回了 Windows 5。为区分文件读写失败和 Shell 启动失败，我在原入口和权限模式下新建空工作区，把复核减到同一个文件、三个工具调用。诊断在 22:30:07 提交，22:30:16 收到结束事件并退出，退出码 0。这是第六周新增的一个有效产品诊断回合，单独统计。[原试现场](../../public/five-surface-20261119/transfer-20261119-dsh-r1/native-events.excerpts.json) · [投递前登记](https://github.com/llongwang751-arch/tx-harness/commit/be41734e820f0bcfb74130fe01083f4e7da60935) · [本次提示词](../../supplements/dsh-shell-diagnostic-v1/prompt.txt)

| 调用 | 结果 | 原生 SDK 源行号 |
|---|---|---|
| 文件工具 `write` | `Created file`。会话结束后核对工作区里的 `probe.txt`，原字节符合请求 | 21、22 |
| 文件工具 `read` | 读取同一 `probe.txt` 并返回标记 `DSH-TOOL-CONTROL-741` | 27、28 |
| `pwsh` | `Get-Content -Raw -LiteralPath './probe.txt'` 返回 `SetNamedSecurityInfoW failed (Win32 5): grantWrite(...)`，没有返回文件文字 | 33、36 |

三次调用在同一 SDK 会话和工作区内，保持 `workspace-write`、请求 `deepseek-flash`、关闭工具侧 Web、保留随包 Skill。事件中的调用 ID 可以对应到返回，绝对路径已脱敏。外部核验确认原件仍是写入的字节。只读 PowerShell 命令也触发了 `grantWrite` 错误，因此可以把本次故障定位到 Shell 的启动授权环节。究竟是哪条 ACL 或执行身份触发拒绝，证据仍不足。该结果适用于这次 Windows SDK 工作区，桌面入口和其他机器没有做同样对照。[现场回执](../../public/dsh-shell-diagnostic-v1/observation.json) · [配对事件](../../public/dsh-shell-diagnostic-v1/native-events.excerpts.json) · [原件](../../public/dsh-shell-diagnostic-v1/probe.txt)
