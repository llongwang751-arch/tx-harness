# DSH 商户结算对账实测

2026 年 11 月 21 日 19:54–19:55（北京时间），使用现有 DeepSeek 账号启动 Windows 桌面安装包自带的 DSH SDK。权限诊断完成 1 次，随后独立计入 1 次有效工程任务。业务任务实测约 15.5 秒，原件复算 **100/100**。新用例沿用 Codex 对账题的原提示词、11 笔订单规模、五级排除规则、三份交付契约和五项权重，换用新的订单、商户和数值。[先于实测提交的登记](../../supplements/dsh-locked-settlement-v1/registration.json) · [用例和输入](../../supplements/dsh-locked-settlement-v1) · [Codex 对账记录](settlement-sealed-run-2026-11-21.md)

| 观察 | 实测 | 置信依据 |
|---|---|---|
| 账号能执行真实任务 | SDK 使用当前账号初始化，两轮都返回 `completed`，随后以退出码 0 结束 | 高。运行回执含请求配置、两次终态、时间和原生日志行号。从回执可以确认账号可用，底层模型只记录请求值 `deepseek-flash`。 [运行回执](../../public/dsh-locked-settlement-20261121/observation.json) |
| DSH 能读输入，四份实际评分文件读不到 | 原生 `read` 读出输入策略，打开评分脚本、细则、Oracle 和参考数据均返回 `EBUSY` | 高。五个原生调用与回执逐一对应。评测器在 SDK 启动前、投递前和 SDK 退出后三次确认 Windows 返回 32。锁释放后重新可读，资产哈希一致。 [原生读回执](../../public/dsh-locked-settlement-20261121/probe-events.json) |
| 业务执行完成 | 读三份输入，PowerShell 一次调用报错，随后使用原生文件工具产出并回读三份文件。三份输入和题面哈希保持一致 | 高。SDK 调用事件和收集的文件可交叉核对。一次调用失败仍记录在现场。 [任务事件](../../public/dsh-locked-settlement-20261121/task-events.excerpts.json) · [三份原件](../../public/dsh-locked-settlement-20261121/outputs) |
| 结算正确 | 正常 5 笔、排除 6 笔、手续费 630 分、应付 32,810 分。入账订单 20/20，逐笔金额 25/25，排除规则与优先级 20/20，汇总数值 25/25，内部对账 10/10 | 高。四份评分资产的哈希在投递前登记，任务结束和解锁后再运行判卷器。原件、评分配置和得分均可重算。 [评分结果](../../public/dsh-locked-settlement-20261121/score.json) · [评分资产](../../public/dsh-locked-settlement-20261121/grader-assets) |

原低完整性配置的 SDK 显示 `ACCOUNT_SIGN_IN_REQUIRED`。这次保留当前 Windows 用户和 SDK 的默认登录状态，由评测进程持续持有四个评分文件的独占读取句柄。Windows 在文件打开时执行共享限制。诊断把路径交给 DSH 当场尝试，结论覆盖这四个文件在本场运行期间的内容访问。对评分目录和整个系统的隔离能力仍未知。Codex 上一场和 DSH 本场的产物各得 100/100，隔离机制、模型及内置 Skill 配置存在差异，单次成绩只能支持各自配置下的任务结果。T03-M 正式场仍待独立复核。

在仓库根目录复算两份工程证据及得分。

```bash
python -B scripts/audit_settlement_evidence.py
```
