# DSH SDK 在低完整性环境下的隔离验证

2026-11-21 · 李明远

DSH SDK 已在新的 Windows 低完整性环境启动并正常退出。它的原生 `read` 先读到工作区输入，随后打开合成评分文件时返回 `EPERM`。相同身份下，独立的 Windows `CreateFileW` 预检对该评分文件返回 Win32 5。中完整性对照能打开并读取同类评分文件。实际接受并完成 2 次诊断，其中受限场 1 次。D 盘旧评测根下的 2 次标签设置失败均发生在投递前，单列。[冻结方案](../../supplements/dsh-mic-isolation-v1/protocol.md) · [临时目录复试登记](https://github.com/llongwang751-arch/tx-harness/commit/9826a8159f93d881e309e3ddf2b1de28125edf25)

| 观察项 | 中完整性对照 | 低完整性隔离 |
|---|---|---|
| Windows 预检 | RID 8192，输入哈希吻合，打开评分文件返回 0 | RID 4096，输入哈希吻合，打开评分文件返回 5 |
| DSH 原生 `read` 输入 | 返回原始随机标记 | 返回原始随机标记 |
| DSH 原生 `read` 评分文件 | 返回合成评分标记 | 打开同一目标返回 `EPERM`，无评分标记 |
| 会话终态 | 两次读取，三次本地固定响应请求，退出码 0 | 两次读取，三次本地固定响应请求，退出码 0 |
| 现场 | [回执与工具事件](../../public/dsh-mic-isolation-v1/dsh-mic-control-r2/observation.json) · [Windows 输出](../../public/dsh-mic-isolation-v1/dsh-mic-control-r2/gate.stdout.jsonl) | [回执、实际 SDK 令牌与工具事件](../../public/dsh-mic-isolation-v1/dsh-mic-restricted-r2/observation.json) · [Windows 输出](../../public/dsh-mic-isolation-v1/dsh-mic-restricted-r2/gate.stdout.jsonl) |

## 为什么这次能启动

之前的外层沙箱阻断了 Electron 解析 C 盘根路径所需的访问。新环境让原有程序依赖按正常路径读取，只对新建空测试目录和合成评分文件设置完整性标签。两个参试目录均可由 Low 进程写入，两份合成评分文件均加 `Medium + No Read Up + No Write Up`。隔离臂在 SDK 执行前查询实际子进程令牌，确认 RID 4096，保留了核查结果。[上一次启动报错](dsh-os-isolation-2026-11-21.md) · [Microsoft 完整性控制说明](https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control)

固定响应只向 DSH 派发两次指定的读取，没有调用真实模型或账户。实际工具事件按调用 ID 配对，宿主机还核对了工具请求路径和回复中的规范化路径指向同一文件。合成标记均在运行结束后公开。结论限于 DSH SDK 及带相同完整性标签的指定文件，整个宿主机的文件隔离、DSH 桌面入口及真实评分资产仍需要各自的验收证据。

```text
python scripts/audit_dsh_mic_isolation.py
```
