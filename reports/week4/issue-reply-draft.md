# Issue #1 回复草稿（2026-11-07）

> 用途：第4周交付完成后，由本人粘贴到 Issue #1 作为评论。不代发。发送前可按需删减；链接均为 codex/evaluation 分支上的相对路径，粘贴时可保留原样。

---

感谢详细的批改。四条"新的问题"与四条"下周要求"逐条回应如下（对应交付已推送到 codex/evaluation 分支，统一截止时点 2026-11-07 09:00 UTC+8）：

**问题1（47条中哪些是本周实际新增）**：新增[运行逐条清单](../blob/codex/evaluation/ledger/run-inventory.md)，47 条运行逐条列出发生日期、轨道、判定、首次入账提交与窗口归属：历史材料入账 39 条（10-13 端到端 25 条、10-21 原生 4 条、10-23 校准+固定契约 10 条），第 3 周真实新增仅 8 条（10-30 DSH 同题重复）。`python scripts/verify_run_inventory.py --check` 可复核清单与台账、入账提交三方一致。

**问题2（39/47 与 252 的快照对应）**：39→41→45→47 对应 10-31 当天四个入账提交（0e658db→18fadd3→a3c88b0→b5e8f7b），不同材料写于当天不同时刻，各引各的数——这是口径冲突的根源，已在[阶段报告修订记录](../blob/codex/evaluation/reports/week3/stage-report.md)与 CL-01 pin_note 里补齐序列。252 项自测是 unittest 套件的捕获快照，现带 captured_on 字段（[self-test.json](../blob/codex/evaluation/ledger/self-test.json)），重跑 `python -m unittest discover -s tests` 即得当日计数，不跨周累计。

**问题3（谁可以独立复核 CL-01/02）**：[复核操作单与签署表](../blob/codex/evaluation/ledger/independent-review/2026-11/README.md)已入库：clone + 两条 reproduce 命令 + 一条 --check，输出规范化哈希与冻结值机械比对（附 verify_output_hash.py，规避 Windows CRLF 管道导致的哈希假性不匹配）。作者已在干净克隆验证自包含性；复核人执行后签署归档到同目录。AI 辅助检查不替代这一步。

**问题4（哪类真实行为能改变判断）**：在[行为协议 v1](../blob/codex/evaluation/supplements/behavior-protocol-v1/README.md)里以两条标准（产物可冻结核验、伪完成可被暴露）排序四类行为：多步工具链第一（已派生 T03-M/T05-M，继承输入逐字节复制、业务数值复用已过双闸门的 T05 oracle，诱饵与注入冻结时写死，防挑刺激条款入库）；伪完成第二（检测结构已内嵌在两变体中）；失败重试与跨任务状态推迟（外部产品故障不可注入/会话不可控）。双闸门通过（空跑 0、参考解 60/60），`python scripts/audit_behavior_protocol.py --check` 可复核。**按"先冻结再决定是否运行"的要求，本周未运行**；10 个实验位是否启动由 2026-11-14 决策门决定。

**下周要求 1（同截止时点版本）**：逐条清单、阶段报告修订（页首留修订记录，含"统计到10-30且零新增"冲突的修正）、正式表、[第4周周报](../blob/codex/evaluation/reports/weekly/2026-11-07.md)统一对齐 2026-11-07 09:00 UTC+8；本周新增运行 ID 逐条如实为**零**（第4周窗口内无产品运行），不以台账总量替代周增量。

**下周要求 2（同事复核）**：操作单已备好，状态"待同事执行"；完成后签署表与输出文件归档于 ledger/independent-review/2026-11/。哈希一致则引用，不一致则开 unknowns 记录并回应，不静默刷新 expected_output_sha256。

**下周要求 3（行为协议先行）**：协议含模型/Skill 可控范围（照实写"均未证实"）、停止条件四条、运行数形状（5产品×2变体×1次=10位，重复仅限 unknown 补跑一次）、失败定义（失败/环境无效/未知三分），运行前四步预登记（case_ids 入册、v3 守卫映射走修订档案、双闸门复验、逐条登记）。

**下周要求 4（判卷覆盖范围）**：[正式比较表](../blob/codex/evaluation/reports/week3/formal-table.md)新增"判卷覆盖范围"一节，并同步为 formal-table.json 的 `grading_coverage` 字段（生成器级实现，`ledger.py --check` 校验一致性）：产物分=冻结文件契约（60分逐项二值）；40分人工维度在正式表未评；四道门槛与双闸门的含义逐行写明"能证明什么、不能由此声称什么"，不以门槛测试表述判卷器整体有效性。

另如实报告一处自查发现：CL-01 的预期哈希随台账入账持续变化，期间我们未按自己的 pin_note 规则逐次"另记差异"（观察文字曾滞后、阶段报告曾引用首刊哈希）。演化史已在 CL-01 pin_note 补记，其中一处判定分布笔误（41条时刻应为 31/5/5）一并修正。
