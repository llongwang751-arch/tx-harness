# 报告阅读索引

当前交付以[书面竞品评测报告v2](report.md)为准，方法见[已执行方案](../docs/evaluation-plan.md)。它覆盖原25个选定产品×任务现场，以及另行预登记的21轮补测；没有五产品纯Harness因果排名。

第二周先读[2026-10-22阶段报告](week2/stage-report.md)：含判卷漏洞的固定反例和开关验证、完整证据绑定、运行计数及未知管理。它补充评测方法，不覆盖旧产品现场和分数。

| 文件 | 用途和口径 |
|---|---|
| [report.md](report.md) | 当前书面报告：差异、旧分与理由、边界观察、补测及归因限制 |
| [窗口重开与续接](window-reopen-v1.md) | 2次真实WorkBuddy桌面任务；两次文件通过，W02干预未知，不能作配对因果结论 |
| [grader-audit-v3.md](grader-audit-v3.md) / [JSON](grader-audit-v3.json) | 22组合成判卷样例、20次守卫开关与25份旧原件复算；均不算新增产品运行 |
| [第二周结论与来源](week2/claims.json) / [计数](week2/counts.json) | 六条有界结论及规则、输入、配置、现场、产物、理由；周报新增产品运行2，有效1、未知1 |
| [evaluation-v2.md](evaluation-v2.md) / [JSON](evaluation-v2.json) | 原25现场的逐字段、声明权重、共同界面和计时复核；严格截止分均为null |
| [exploratory-score-review.md](exploratory-score-review.md) / [JSON](exploratory-score-review.json) | 冻结的旧26次评分，含额外豆包本地T01失败；仅25个选定组合用于描述均值 |
| [补测分母](../public/supplements/contracts-v2/README.md) / [JSON](../public/supplements/contracts-v2/coverage.json) | S01五产品各三轮及S02三组许可对照；E2原件与E1资格分开，无综合分 |
| [证据定位审计](../public/supplements/contracts-v2/evidence-locators.md) | 2026-10-20补公开的6份既有附件；逐条文件/event定位与人工说明区分 |
| [permission-pairs-v2.json](permission-pairs-v2.json) | 三组许可对照实际记录条件的事后核对，不是新的实验 |
| [harness-observations.md](harness-observations.md) | DSH旧现场请求、写入及错误映射；调用数不是独立样本数 |
| [weekly/](weekly/README.md) | 本人已确认发送的邮件周报Markdown归档；后续修订不冒充原邮件 |

旧评分JSON的`review_coverage_state`及`full_five_product_five_case_coverage_completed`仍是早期“未齐备”状态，与同文件最后已补齐的25组合记录不一致。这两个历史状态字段不作为当前覆盖结论；原文件为保留评分版本未重写。当前25/25依据25条选定记录及其实际原件，见evaluation-v2.json的runs和公开包索引；21/21补测依据coverage逐位manifest复核。

以下是历史或未执行草案的材料，不能据其0/75表格判断当前项目未做测试：

| 文件 | 应如何阅读 |
|---|---|
| [report-v1-2026-10-14.md](report-v1-2026-10-14.md) | 旧报告原文，与原提交字节一致；当前解释以v2为准 |
| [summary.md](summary.md) / [summary.json](summary.json) | 未实施75轮确认性草案的工具汇总，因此是0/75；不是25+21轮现有数据汇总 |
| [verification.md](verification.md) | 2026-10-13当日工具验证记录，不代表当前证据包/测试总数；当前CI以实际提交为准 |

本次20日审查没有重做产品实验，没有修改封存包、旧评分或已发邮件正文。变动见[CHANGELOG](../CHANGELOG.md)。
