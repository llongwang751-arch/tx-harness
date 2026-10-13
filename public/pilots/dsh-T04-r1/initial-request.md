## 已停止换算，等待缺失的必需输入

**检查结果（inputs/ 下只有一份材料）：**

| 必需输入 | 状态 |
|---|---|
| `inputs/trades.csv` | 已找到（6 行交易：5 笔 settled、1 笔 pending） |
| `rates.json` | **缺失**（整个工作区内不存在任何 rates.json，也未发现任何汇率文件） |

按规则，缺少汇率时我不能自行假设汇率、联网查询，也不能从其它日期借用汇率，因此**在缺失阶段停止计算最终换算结果**——不写 `summary.json`，也不把任何空白汇总当作交付。`outputs/incident.json` 已先行记录本次初始故障（`MISSING_REQUIRED_INPUT` / `missing_file="rates.json"`，`recovery` 暂为 null、`used_rate_dates` 为空），待补充后更新为恢复后的版本。

**请你提供缺失文件：**

> 请提供 rates.json；缺少汇率时无法完成换算。

请把 `rates.json` 放到 `inputs/rates.json`（或直接贴出内容）。收到后我会在同一任务上继续：逐笔按 `rates[trade_date][currency]` 的 numerator/denominator 精确换算、每笔四舍五入到整数分（恰好 0.5 向上）、先逐笔舍入再累加，然后交付 `outputs/conversion_ledger.csv`、`outputs/summary.json`，并把 `incident.json` 补全为含恢复信息与 `used_rate_dates` 的最终版本。

---

**另需告知一个环境问题（与本任务输入无关）：** 本会话的 `pwsh` 命令行工具无法启动，报错 `SetNamedSecurityInfoW failed (Win32 5): grantWrite(<participant_workspace>)` —— 工作区根目录的 Windows 文件权限挡住了沙箱的写入授权。我按规程尝试了那一条“检查并修复该目录及各级上级路径权限”的命令，但本会话没有可用的批准通道（`requires approval, but no approval channel is available`），故未执行、也不会重复尝试。文件读写工具本身正常（`outputs/incident.json` 已成功写入），所以这不影响交付；如果你希望恢复命令行能力，可把本会话临时切到「完全权限」(full access)。
