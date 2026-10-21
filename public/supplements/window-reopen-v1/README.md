# WorkBuddy窗口重开实测｜2026-10-22

真实提交2次；有效通过1、失败0、未知1。两次文件验收通过，W02干预条件未知，所以不报告关窗效果或成功率。

| 运行 | 状态 | 现场与原件 |
|---|---|---|
| W01-control | 有效，通过 | [现场包](W01-control/README.md) |
| W02-window-reopen | 文件通过，干预条件未知 | [现场包](W02-window-reopen/README.md) |

[冻结协议](../../../supplements/window-reopen-v1/protocol.md) · [登记提交](https://github.com/llongwang751-arch/tx-harness/commit/c6d3215523ec75dbe4bae009d9474c04aab6108f) · [分析报告](../../../reports/window-reopen-v1.md) · [运行索引](index.json)

每个包包含公开原件、逐次取回副本、收集日志及封存清单、配置与提交记录、判卷和逐项判断。截图是经检查的原生截图原件；完整AX含账户及其他任务，只公开逐行审阅的研究任务摘录，并保留源文件SHA和行号。单人采集的局限仍然保留。

运行`python scripts/verify_window_reopen.py`可检查登记版本、输入、封存覆盖、字节哈希、续接时间、结果和未知计数的一致性。脚本通过不等于外部独立证明桌面行为真实。
