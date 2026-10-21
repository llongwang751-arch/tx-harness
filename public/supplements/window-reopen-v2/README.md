# 窗口重开v2公开现场

作者：李明远。2026-10-22通过官方原生Computer Use真实执行，先R01重开、再R02保持窗口，一次一个任务。首次发送前冻结登记提交为[51cd34f](https://github.com/llongwang751-arch/tx-harness/commit/51cd34f436f22f66f22dddd8e2d14a94535a362c)。[完整报告](../../../reports/window-reopen-v2.md)说明判定与限制。

| 实际任务 | 运行条件与主观察 | 联合文件交付 | 入口 |
|---|---|---|---|
| R01-reopen | 有效、通过；启动前连续两份空窗口清单 | 通过；690.030秒内封存 | [review](R01-reopen/review.json)、[关窗记录](R01-reopen/close-proof.json)、[manifest](R01-reopen/manifest.json) |
| R02-control | 有效、通过；保持窗口 | 通过；380.422秒内封存 | [review](R02-control/review.json)、[保持窗口记录](R02-control/control-proof.json)、[manifest](R02-control/manifest.json) |

每包包含四份`collected/retrieval-before|retrieval-after`原生另存副本，以及最终三份`collected/stage-b`原件；`outputs`是最终三份的公开展示副本，不额外计一次收集。`collection.jsonl`与`seal.json`逐项对应；`ui-retrieval.json`绑定原消息附件/原生交付卡来源、另存目标、字节和时间。`scene-index.json`把原采集定位映射到公开AX摘录，摘录带源SHA、原行号与采集时间。

截图为经隐私检查的原生原图。AX只公开任务相关逐行摘录，完整原始源留私有；它们仍是Operator与AI辅助采集，不是独立外部认证。没有新操作方模型提交的主观察不代表不存在隐藏后台模型活动。源文件一直存在，不能从原生取回推成独立云存储保存；Stage B是模型、Skill和Harness联合结果。

本批新增独立产品运行2次，有效通过2次、失败0、未知运行0；云存储指标仍未知。另两次[v1](../window-reopen-v1/README.md)原样保留，W02干预未知不追补、不被新结果替换。本周合计4次，有效通过3、未知1。

复核：`python -X utf8 scripts/verify_window_reopen_v2.py`。输入、判定和预算见[冻结协议](../../../supplements/window-reopen-v2/protocol.md)。
