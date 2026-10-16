# 五款 Harness 竞品评测

个人开源仓库：[llongwang751-arch/tx-harness](https://github.com/llongwang751-arch/tx-harness)。比较对象为Codex、WorkBuddy、DeepSeek Harness（DSH）、元宝专家模式、豆包工作任务模式；用户已确认公告中的“豆包办公”指工作任务模式。

截至2026-10-16，原五产品五题的25个选定组合、31个公开证据包及26次旧评分已保留。当前[报告v2](reports/report.md)以Harness边界观察为主，[派生复核](reports/evaluation-v2.md)另列字段差异、声明权重和时间证据。另行预先登记21个固定文件契约/权限对照实验位，真实封存进度见[补测索引](public/supplements/contracts-v2/README.md)；计划和准备不计完成。

[2026-10-16方法修订](docs/revision-v2.md)保留旧协议、用例、原件及分数，并分别呈现共同界面契约、额外执行链、业务错误和证据缺口。[旧分析口径](docs/exploratory-analysis-plan.md)及[旧报告原文](reports/report-v1-2026-10-14.md)仍可追溯。模型、Skill和权限未匹配的部分保持因果未知；不发布五产品纯Harness排名。

阅读[书面报告](reports/report.md)和[现场证据索引](public/pilots/README.md)，复核原生交付、现场事件、失败attempt与归因边界。

## 归因原则

模型、Skill、工具权限和Harness会共同影响结果。无法把五产品换成同一模型和同一Skill时，主实验只能比较固定配置的端到端表现。研究者通过现场证据定位故障，再用同模型/同Skill的匹配对照或Harness内消融验证候选原因。没有对照的推测标为待验证，不声称已剥离模型影响。

详见[方案](docs/protocol.md)、[归因定责](docs/attribution.md)、[Harness 执行链归因补充](docs/harness-attribution-supplement.md)、[打分细则](docs/rubric.md)和[产品来源](docs/products.md)。补充方法把输入传递、请求执行、文件落地、错误反馈和状态保存作为观察主体；业务答案正确与否另记。[已实施的执行链复核](reports/harness-observations.md)逐项列出 DSH 六轮预试的写入与错误反馈对应，后续正常编辑不会被算作写入失败。官方能力介绍仅用于锁定入口，不代替实测。

## 作业材料映射

| 要求 | 材料 | 当前状态 |
|---|---|---|
| 评测方案 | docs/protocol.md、config/protocol.json、docs/exploratory-analysis-plan.md | 确认性草案未实施；本次按探索性口径复现和追溯 |
| 用例：任务、输入、完成条件 | cases/T01至T05，prompt.md、inputs、case.json | 已设计；可离线核验 |
| 表现现场 | public/pilots真实接入记录 | 31个包；25/25组合完成，失败、诊断和预算局限保留 |
| 赋分、标准、理由 | config/rubric.json、docs/rubric.md、reports/exploratory-score-review.json | 26次逐项审阅；缺证项保留null及范围 |
| 书面竞品报告 | reports/report.md、reports/evaluation-v2.json | Harness边界为主，业务及旧分辅助；新补测进度单列 |
| 每周六个人周报邮件 | reports/weekly-template.md、reports/weekly-2026-10-17-draft.md | 仅本地模板/草稿；未发送 |
| 个人开源GitHub链接 | https://github.com/llongwang751-arch/tx-harness，MIT | 公开方案、代码、真实预试与报告 |

## 快速开始

需要Python3.11或以上，无外部Python依赖。请从仓库根目录运行：

```powershell
python -m harness_eval audit
python -m unittest discover -s tests -v
python scripts/analyze_evaluation_v2.py --check
python scripts/verify_contracts_v2.py --check
python scripts/analyze_permission_pairs_v2.py --check
python -m harness_eval --help
```

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
tests/          验收判定与证据门槛的回归测试
reports/        完整探索性报告、逐项评分、周报与确认性草案
runs/           本地采集包（Git忽略）
public/runs/    经审查导出的公开证据包（可提交）
private/        私有原始记录（Git忽略）
```

Hash帮助复核版本与文件一致性，无法证明记录者没有造假。任务和答案公开也有记忆污染风险，因此本套任务用于过程诊断，不作模型能力通用排行榜。正式报告注明作者、采集日期、账号条件、入口、版本与研究局限。
