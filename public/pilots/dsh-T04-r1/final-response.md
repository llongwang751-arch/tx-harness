已收到补充的 `inputs/rates.json`，在原任务上继续完成换算。inputs/ 未做任何修改。

## 恢复记录
- 初始故障：`outputs/incident.json` 的 `initial_blocker`（`MISSING_REQUIRED_INPUT` / `missing_file="rates.json"`）——故障阶段已停止计算，未产出空白汇总。
- 恢复：`recovery` = `{"input":"rates.json","method":"provided_by_user"}`，由对话现场的实际请求与本次补充共同佐证。
- `assumptions` 为空（未做额外假设，未联网、未跨日期借用汇率）；`used_rate_dates` = `["2026-10-01","2026-10-02"]`。

## 逐笔换算（先逐笔四舍五入，再累加）
| trade_id | 日期 | 币种 | 金额(最小单位) | 状态 | 汇率 | cny_cents |
|---|---|---|---|---|---|---|
| F001 | 2026-10-01 | USD | 10000 | settled | 7/1 | 70000 |
| F002 | 2026-10-01 | EUR | 5000 | settled | 8/1 | 40000 |
| F003 | 2026-10-01 | CNY | 12345 | settled | 1/1 | 12345 |
| F004 | 2026-10-02 | USD | 3350 | settled | 701/100 | 23483.5 → **23484**（恰好 .5 向上） |
| F005 | 2026-10-02 | EUR | 101 | settled | 799/100 | 806.99 → **807** |
| F006 | 2026-10-02 | USD | 1000 | pending | — | 0（rate 两列写 `-`，不换算） |

## 一致性核对
- 台账 6 行，`trade_id` 唯一（F001–F006 各一行）；`included` 为小写 true/false。
- 合计：70000+40000+12345+23484+807 = **146636**。
- by_currency：CNY 12345 + EUR 40807 + USD 93484 = 146636 ✓（settled 各自笔数 1/2/2，共 5）
- by_date：2026-10-01 = 122345（3 笔）+ 2026-10-02 = 24291（2 笔，pending 不计）= 146636 ✓
- included_count=5，excluded_count=1。

## 交付物（均在 outputs/）
- `outputs/conversion_ledger.csv` — 9 列，每 trade_id 恰好一行
- `outputs/summary.json` — currency=CNY，分组按币种、日期排序，分组只含 settled
- `outputs/incident.json` — 含初始故障与恢复声明

说明：本会话的 `pwsh` 仍因工作区根目录的 Windows 文件权限问题无法启动（无批准通道，未重试修复），因此以上核对通过重新读取交付文件与精确有理数手算完成，不影响结果正确性。
