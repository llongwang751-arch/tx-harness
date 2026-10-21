# 五款 Harness 竞品评测

作者：李明远。个人开源仓库：[llongwang751-arch/tx-harness](https://github.com/llongwang751-arch/tx-harness)。比较对象为Codex、WorkBuddy、DeepSeek Harness（DSH）、元宝专家模式、豆包工作任务模式；用户已确认公告中的“豆包办公”指工作任务模式。

2026-10-21第二周更新：[阶段报告](reports/week2/stage-report.md)及[验收要求映射](supplements/week2/requirements.md)。本周新增产品实测0；新增22组评测侧合成答案，复现并修正三类判卷缺口，20次守卫开关核查及25份旧产物复算另列。六条结论绑定完整来源，五项未知设定下一步和停止条件；[10月24日文字周报](reports/weekly/2026-10-24-draft.md)仍为草稿，数据截至21日，不发送PDF。

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
| 每周六个人周报邮件 | reports/weekly/README.md、reports/weekly/2026-10-17.md、reports/weekly-template.md | 10月17日周报已发送，正文已按本人确认版本以Markdown归档 |
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
python scripts/analyze_permission_pairs_v2.py --check
python -m harness_eval --help
```

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
