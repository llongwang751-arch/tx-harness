# DSH SDK 文件工具与 Shell 检查

运行 ID `diag-20261119-dsh-file-vs-shell-r1`。一次真实 SDK 会话，单独于文件收发专项和 T03-M 正式任务。用新的外部工作区、已安装的 DSH SDK、`workspace-write`、`deepseek-flash` 请求值。沿用文件收发场的 SDK 工具和 Skill 配置。

在空目录中先用内置文件工具写入，再用内置文件工具读取同一个 `probe.txt`。最后只用一次 `pwsh` 执行只读的 `Get-Content -Raw -LiteralPath './probe.txt'`。确认工具调用和返回，并在产品会话之外核验文件原字节的摘要。Shell 请求不得修改文件、权限或提权。

如果文件写入及回读成功，且同一工作区的只读命令返回 `SetNamedSecurityInfoW` / Win32 5 / `grantWrite`，记录为 Shell 启动授权错误再次观察到。只有 Shell 实际返回文件内容才算本次未复现。缺调用、输入不一致、无终态或其他错误时，按实记录。只投递一次，记录后停止。该对照定位到工具路径及报错环节，Windows ACL 拒绝的根因仍需其他证据。
