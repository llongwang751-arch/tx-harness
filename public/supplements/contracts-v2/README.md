# 固定文件契约补测现场

协议预先登记21位；当前公开封存16/21。未封存不等于失败或未开始。旧31个pilot包和旧25组合另列，不混作独立重复。

S01为五产品各三次固定读写/缺失文件反馈；S02为Codex三组允许/拒绝写权限配对。仅在实际目标操作出现时检查E1契约；GUI内部参数未知，保留E2。没有综合分或纯Harness排名。

| 实验位 | 公开状态 | echo原字节 | receipt声明 | 真实缺失读取反馈 | 写入/许可观察 |
|---|---|---|---|---|---|
| [S01-codex-r1](S01-codex-r1/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-codex-r2](S01-codex-r2/README.md) | 已封存 | 通过 | 通过（仅声明） | pass | unknown / not_applicable |
| [S01-codex-r3](S01-codex-r3/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-doubao-r1](S01-doubao-r1/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-doubao-r2](S01-doubao-r2/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-doubao-r3](S01-doubao-r3/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-workbuddy-r1](S01-workbuddy-r1/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-workbuddy-r2](S01-workbuddy-r2/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-workbuddy-r3](S01-workbuddy-r3/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-yuanbao-r1](S01-yuanbao-r1/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-yuanbao-r2](S01-yuanbao-r2/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-yuanbao-r3](S01-yuanbao-r3/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / not_applicable |
| [S01-dsh-r1](S01-dsh-r1/README.md) | 已封存 | 通过 | 通过（仅声明） | upstream_deviation | pass / not_applicable |
| [S01-dsh-r2](S01-dsh-r2/README.md) | 已封存 | 通过 | 通过（仅声明） | pass | pass / not_applicable |
| [S01-dsh-r3](S01-dsh-r3/README.md) | 已封存 | 通过 | 通过（仅声明） | pass | pass / not_applicable |
| [S02-codex-r1-allow](S02-codex-r1-allow/README.md) | 已封存 | 通过 | 通过（仅声明） | unknown | unknown / pass |
| S02-codex-r1-deny | 未封存 | 未知 | 未知 | 未知 | 未知 |
| S02-codex-r2-deny | 未封存 | 未知 | 未知 | 未知 | 未知 |
| S02-codex-r2-allow | 未封存 | 未知 | 未知 | 未知 | 未知 |
| S02-codex-r3-allow | 未封存 | 未知 | 未知 | 未知 | 未知 |
| S02-codex-r3-deny | 未封存 | 未知 | 未知 | 未知 | 未知 |

未取得原件不等于字节错误；应按普通输出卡、取回过程和逐包限制区分未交付与收集受阻。S02拒绝臂没有文件可能符合许可契约。产品自述not_found或external_actions=[]不证明实际工具错误/无外传；请按逐包事件和observations的具体定位复核。

逐指标分母见coverage.json的metric_denominators：计划、公开已启动、未封存、明确适用/适用未知、eligible、passed、failed、上游偏离、未知及明确环境无效分别列出。环境状态未明示不推定为有效；计时采集中断也不自动使已留存的每个工具事件无效。条件通过率只在eligible有已知判定时计算，eligible=0为null；同时保留进入该段之前的缺口。public_started只数已封存且可公开复核的真实提交，不推断未封存位尚未执行。

GUI选段的received_at是实际采集时刻；较早公开包的记录顺序可能按阅读段落排列，复核时间线应按received_at还原。当前导出器自动按该时刻排序；既有包不覆盖。

复核：`python -X utf8 scripts/verify_contracts_v2.py --check`。登记、输入、产物和投影SHA定位版本，仍依赖Operator采集，不是独立系统审计。
