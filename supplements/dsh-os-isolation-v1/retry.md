# DSH 受限启动校准后的第二组

第一组原生对照两次读取均成功。外层隔离命令确认输入可读和保护文件返回 `0x80070005`，但受限 Electron 在 SDK 初始化前对 `C:\` 执行 `lstat` 时返回 EPERM。

追加两场新 ID `dsh-os-isolation-control-r2`、`dsh-os-isolation-restricted-r2`。两场均加 `--preserve-symlinks --preserve-symlinks-main`，其余沿用第一组规则及隔离配置。权限范围不变，评分文件可达性仍由原生读取对照决定。第一组及其启动错误完整保留。每个新场只提交一次，先原生对照，后受限场。
