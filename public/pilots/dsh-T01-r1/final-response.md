已完成。三份交付文件已写入 `outputs/`，`inputs/` 未改动（工作区只有 inputs 原件、prompt.md 与 outputs 三个文件，无多余产物）。

## 计算结果

**order_ledger.csv**（6 行，每个 order_id 恰好一行）

| order_id | group | status | gross | refund | net | included |
|---|---|---|---|---|---|---|
| O101 | retail | paid | 15000 | 2000 | 13000 | true |
| O102 | retail | shipped | 8800 | 2000 | 6800 | true |
| O103 | business | cancelled | 10000 | 0 | 0 | false |
| O104 | business | paid | 4500 | 0 | 4500 | true |
| O105 | retail | pending | 6500 | 0 | 0 | false |
| O106 | business | shipped | 22000 | 3000 | 19000 | true |

**aggregate.json**：total = 4 单 / gross 50300 / refund 7000 / net 43300；groups 按升序为 business（2 单，26500/3000/23500）与 retail（2 单，23800/4000/19800）。

**exceptions.json**：订单完全重复 1、订单被替代 1、退款完全重复 1、退款被替代 1；orphan=`["R007"]`（指向 O999）、非成功=`["R004","R006"]`（failed/pending）、订单不合格=`["R008"]`（指向已 cancelled 的 O103）。三类互不重叠。

## 校验情况（请留意）

- 我已用独立子代理从 `inputs/` 重新手工推导一遍，逐字段与交付文件完全一致（台账 6 行、total、两个分组、7 项异常全部吻合）。
- 但**无法用命令行做程序化解析校验**：本会话的命令行运行被 Windows 文件权限挡住，脚本在给工作区根目录 `D:\harness-participants\pilot-dsh-T01-r1` 设置权限时报「拒绝访问（错误 5）」。修复脚本需要更宽访问权限，而本会话没有可用的审批通道，因此该权限问题**尚未诊断清楚**。文件读写工具本身正常，所以交付不受影响。

如果后续还需要在本会话跑脚本（例如再做一次 JSON 解析校验），请把本会话临时切到「完全权限」(full access)，之后既可以直接继续工作，也可以让我接着排查这个文件权限问题；也麻烦把本会话作为反馈发出去，好让我们补上这个场景。
