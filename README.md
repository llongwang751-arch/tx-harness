# 五款 Harness 竞品评测

作者：李明远。个人开源仓库：[llongwang751-arch/tx-harness](https://github.com/llongwang751-arch/tx-harness)。比较对象为Codex、WorkBuddy、DeepSeek Harness（DSH）、元宝专家模式、豆包工作任务模式；用户已确认公告中的“豆包办公”指工作任务模式。

## 30 秒看懂

**结论先读[结论先行](reports/conclusion-2026-10-31.md)**：在“固定配置、单次、只判产物契约”的条件下，产物分 Codex = WorkBuddy = 豆包（各 300/300）> DSH（270/300）> 元宝专家模式（159/300）；在“可归因到 Harness”的条件下没有排名，因为受控轨道只覆盖 Codex/DSH 且两臂无差异。两条结论同时成立，证据与理由在那一页。

| 课题要求 | 入口 | 当前状态 |
|---|---|---|
| 评测方案 | [已执行方案](docs/evaluation-plan.md)、[台账与归因规范](docs/ledger.md)、[补测协议](supplements/contracts-v2/protocol.json) | 25 个选定组合 + 21 轮补测分别统计；归因规则与分账方式成文 |
| 用例：任务、输入、完成条件 | [cases/T01–T05](cases)、[压力层固定契约](supplements/contracts-v2/fixtures) | 题面、输入、答案冻结，可离线核验 |
| 表现现场 | [公开现场包](public/pilots)、[补测现场](public/supplements)、[运行台账](ledger/runs.jsonl) | 41 条运行记录（25 端到端 + 4 主臂 + 6 校准 + 4 原生 + 2 同题重复）+ 31 个公开包 |
| 打分细则与赋分 | [原评分细则](docs/rubric.md)、[判卷修订档案](ledger/revisions/index.json)、[正式比较表](reports/week3/formal-table.md) | 机器检查 60 分逐项；三道守卫有修前/修后与独立验收 |
| 书面竞品评测报告 | [结论先行](reports/conclusion-2026-10-31.md)、[完整报告 v2](reports/report.md) | 先结论后全文；每项判断标置信依据 |
| 每周六个人周报 | [周报索引](reports/weekly/README.md)、[10月31日正文](reports/weekly/2026-10-31-draft.md) | 10月17日已发；10月31日正文就绪，待本人发送 |

2026-10-31整理第三周交付（统计窗口10月25日至31日）：本周新增产品任务2次（DSH T01 同题第2、3次重复，三次 60/60、语义 3/3 一致、字节 2/3 一致），另交付记账方式与一个闭环。41条运行按唯一ID和十个字段登记进[运行台账](ledger/runs.jsonl)，产品运行、自测、离线复算、判卷回归、裸模型探针、接口预检拆成[六本互不相加的账](ledger/accounts.json)；[正式比较表](reports/week3/formal-table.md)只纳入规则冻结、题面有效、证据有效、无污染的运行，29条正式轨道记录全部入选、0条被剔除，五款各有5条可判运行，但因模型未证实、协议为草案，表内给分不给名次。判卷三道守卫补[修订档案](ledger/revisions/index.json)（修前/修后代码、正例、近似错误例、独立验收、历史复算影响），并用[另一套实现](scripts/independent_check.py)复核22例36个判定、0分歧。规范与复核命令见[台账与归因规范](docs/ledger.md)，过程与结论见[第三周阶段报告](reports/week3/stage-report.md)和[10月31日文字周报](reports/weekly/2026-10-31-draft.md)；周报仍由本人发送，未发送不写成已交付。

2026-10-25整理第二周交付（统计窗口10月18日至24日）：新增已接受任务14次，有效9、失败0、未知5。其中真实模型WorkBuddy任务4次，Codex/DSH固定响应任务7次，WorkBuddy固定响应校准3次；后10次没有神经模型推理。两次接受前配置拒绝另列，界面预检计零任务。[文字周报草稿](reports/weekly/2026-10-24-draft.md)、[逐次运行登记](supplements/week2/executions.json)、[阶段报告](reports/week2/stage-report.md)已同步，尚未发邮件，由本人发送。

24日[Codex/DSH四次正式固定动作对照](reports/controlled-adapter-v1.md)均通过成功文件或预期错误契约；[WorkBuddy三次接入校准](reports/controlled-workbuddy.md)均未走通，保留为未知，不给产品判负。[三款GUI接口预检](reports/gui-interface-preflight.md)保留版本、界面原图和入口限制。当前只控制指定工具链路的生成动作，未完成五产品全部统一模型或完整Skill消融，旧分不改。

2026-10-23完成[五产品归因边界核对](reports/attribution-boundaries.md)：逐款列模型请求/标签、Skill部分控制或未知、实际边界和停止条件，核对旧15轮全部尝试。本次新增产品运行0次；未将DSH内置Skill保留写成全部关闭，也未将条件通过率用于纯Harness排名。来源字段、SHA及三轮配置见[JSON](reports/attribution-boundaries.json)。

2026-10-22实测及23日材料更新：[阶段报告](reports/week2/stage-report.md)及[验收要求映射](supplements/week2/requirements.md)。当时新增WorkBuddy原生桌面任务4次，有效通过3、失败0、未知1；[v1](reports/window-reopen-v1.md)保留旧关窗采集缺口，另行登记的[v2一对任务](reports/window-reopen-v2.md)验证直接原生取回及关窗观察，不替换旧未知。另有22组合成答案、20次守卫核查及25份旧产物复算，修正三类判卷缺口；七项未知设定下一步及停止条件。本周最新计数见上方25日整理记录，文字周报由本人发送，不用PDF。

截至2026-10-16，原五产品五题的25个选定组合、31个公开证据包及26次旧评分已保留。另行预先登记的21个固定文件契约/权限对照实验位已全部执行并封存，见[补测索引](public/supplements/contracts-v2/README.md)。当前[报告v2](reports/report.md)以Harness边界观察为主，[派生复核](reports/evaluation-v2.md)另列字段差异、声明权重和时间证据。

[2026-10-16方法修订](docs/revision-v2.md)保留旧协议、用例、原件及分数，并分别呈现共同界面契约、额外执行链、业务错误和证据缺口。[旧分析口径](docs/exploratory-analysis-plan.md)及[旧报告原文](reports/report-v1-2026-10-14.md)仍可追溯。模型、Skill和权限未匹配的部分保持因果未知；不发布五产品纯Harness排名。

阅读[书面报告](reports/report.md)和[现场证据索引](public/pilots/README.md)，复核原生交付、现场事件、失败attempt与归因边界。

仓库更新见[变更记录](CHANGELOG.md)，邮件周报见[个人周报索引](reports/weekly/README.md)。2026-10-17周报已按本人确认的发送版本归档。

## 归因原则

模型、Skill、工具权限和Harness会共同影响结果。无法把五产品换成同一模型和同一Skill时，主实验只能比较固定配置的端到端表现。研究者通过现场证据定位故障，再用同模型/同Skill的匹配对照或Harness内消融验证候选原因。没有对照的推测标为待验证，不声称已剥离模型影响。

详见[已执行的评测方案](docs/evaluation-plan.md)、[归因定责](docs/attribution.md)、[Harness 执行链归因补充](docs/harness-attribution-supplement.md)、[原评分细则](docs/rubric.md)和[产品来源](docs/products.md)。补充方法把输入传递、请求执行、文件落地、错误反馈和状态保存作为观察主体；业务答案正确与否另记。[已实施的执行链复核](reports/harness-observations.md)逐项列出DSH六轮预试的写入与错误反馈对应，后续正常编辑不会被算作写入失败。官方能力介绍仅用于锁定入口，不代替实测。

当前材料支持探索性任务比较和有限许可对照，尚未完成五产品排除模型/Skill干扰的独立因果比较。2026-10-20仓库审查补公开6份原先遗漏、哈希已在旧包登记的核查附件，并新增[公开证据定位检查](public/supplements/contracts-v2/evidence-locators.md)及E2交付分母；封存包、旧分和已发周报未覆盖。各报告的用途及历史状态字段说明见[报告索引](reports/README.md)。

## 作业材料映射

| 要求 | 材料 | 当前状态 |
|---|---|---|
| 评测方案 | [已执行方案](docs/evaluation-plan.md)、docs/exploratory-analysis-plan.md、supplements/contracts-v2/protocol.json | 原25组合及21轮补测分别统计；docs/protocol.md及config/protocol.json为未实施75轮草案 |
| 用例：任务、输入、完成条件 | cases/T01至T05，prompt.md、inputs、case.json | 已设计；可离线核验 |
| 表现现场 | public/pilots、public/supplements/contracts-v2 | 旧31个包及25/25组合、新21/21补测；失败、诊断和预算局限保留 |
| 赋分、标准、理由 | config/rubric.json、docs/rubric.md、reports/exploratory-score-review.json | 26次逐项审阅；缺证项保留null及范围 |
| 书面竞品报告 | reports/report.md、reports/evaluation-v2.json、reports/permission-pairs-v2.json | Harness边界为主，业务及旧分辅助；三组实际许可对照与条件核对单列 |
| 每周六个人周报邮件 | reports/weekly/README.md、reports/weekly/2026-10-17.md、reports/weekly/2026-10-31-draft.md、reports/weekly-template.md | 10月17日周报已发送；10月31日正文已写完待本人发送 |
| 运行台账与归因定责 | ledger/runs.jsonl、ledger/accounts.json、ledger/unknowns.json、docs/ledger.md | 39条运行十字段登记；六账分列；七项未知各带影响/下一步/停止条件 |
| 正式比较表与门槛 | reports/week3/formal-table.md、ledger/formal-table.json | 四道门槛逐行校验；排名门槛无人满足，名次保留为null |
| 判卷修订留档 | ledger/revisions/index.json、scripts/independent_check.py | 三条修订六件套齐全；独立实现复核22例36判定、0分歧 |
| 个人开源GitHub链接 | https://github.com/llongwang751-arch/tx-harness，MIT | 公开方案、代码、真实预试与报告 |

## 快速开始

需要Python3.11或以上，无外部Python依赖。请从仓库根目录运行：

```powershell
python -m harness_eval audit
python -m unittest discover -s tests -v
python scripts/analyze_evaluation_v2.py --check
python scripts/verify_contracts_v2.py --check
python scripts/audit_contract_evidence.py --check
python scripts/audit_grader_v3.py --check
python scripts/verify_week2.py --check
python scripts/verify_window_reopen.py
python scripts/verify_window_reopen_v2.py
python scripts/audit_attribution_boundaries.py --check
python scripts/audit_controlled_adapter.py --check
python scripts/audit_controlled_workbuddy.py --output reports/controlled-workbuddy.json --check
python scripts/verify_gui_controls.py
python scripts/analyze_permission_pairs_v2.py --check
python scripts/ledger.py --check
python scripts/ledger.py reproduce CL-01
python scripts/ledger.py reproduce CL-02
python scripts/independent_check.py
python -m harness_eval --help
```

台账相关命令只读公开文件：`ledger.py --check` 重算 41 条运行记录、四道门槛、六本账、结论哈希与修订档案；`reproduce` 重跑对应结论并打印可比较的输出；`independent_check.py` 用另一套实现复核判卷守卫。

后续新产物的有效性验收入口见[evaluation_v3](evaluation_v3/README.md)，例如`python -m evaluation_v3.grader --case T03 --outputs <产物目录>`。新版看`accepted`，旧数值明确置于legacy_artifact_result中，不把旧60分误读成新增契约通过；新批次须先登记规则和代码版本。

下面保留工具使用方法。若继续开展确认性实验，先锁定版本/模型/技能条件并冻结协议；当前五题比较已经按探索性口径完成。每次 `prepare` 只复制参与者可见的prompt和inputs；oracle和评分程序留在评测员目录。把workspace复制/挂载到隔离的产品目录，不让任何参评产品读这个评测仓库。

```powershell
python -m harness_eval prepare --product codex --case T01 --replicate 1 --track pilot
```

按[现场操作单](docs/collection.md)采集后，填写人工判断、封存、评分。原确认性草案安排五产品×五任务×三次，共75个实验位；公告没有要求这组重复，本次交付不据此追加实验。工具生成顺序、验收与汇总；scripts提供三款本地原生CLI的预试适配器，默认dry-run，显式--execute才执行，不能代替五产品实际操作或自动登录。

## 目录

```text
config/         协议、评分权重、产品入口登记
docs/           方法、归因、采集、评分与提交说明
cases/          五套任务、原始输入、仅供评测员使用的答案
harness_eval/   标准库CLI：准备、记录、核验、封存、打分、汇总
evaluation_v3/  新增验收门槛；保留旧判卷与分数，不另计综合分
tests/          验收判定与证据门槛的回归测试
ledger/         第三周运行台账：41条运行、六本账、正式比较表、未知登记、结论与判卷修订档案
reports/        完整探索性报告、逐项评分、周报与确认性草案
reports/weekly/ 已发送邮件周报的Markdown归档与索引
supplements/    新补测预登记协议、变体输入与提示词
runs/           本地采集包（Git忽略）
public/pilots/  原31个公开现场包
public/supplements/  新21轮补测现场、原件与分母
public/grader-audit-v3/  合成判卷样例，不能当作产品运行
public/runs/    经审查导出的公开证据包（可提交）
private/        私有原始记录（Git忽略）
```

Hash帮助复核版本与文件一致性，无法证明记录者没有造假。任务和答案公开也有记忆污染风险，因此本套任务用于过程诊断，不作模型能力通用排行榜。正式报告注明作者、采集日期、账号条件、入口、版本与研究局限。
