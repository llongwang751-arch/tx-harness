# 五款 Harness 竞品评测

个人开源仓库：[llongwang751-arch/tx-harness](https://github.com/llongwang751-arch/tx-harness)。比较对象为Codex、WorkBuddy、DeepSeek Harness（DSH）、元宝专家模式、豆包工作任务模式；用户已确认公告中的“豆包办公”指工作任务模式。

截至2026-10-14，方案、五套用例、36项机器检查与评分工具已完成。Codex、DSH和WorkBuddy正常桌面均已执行五任务预试。DSH SDK的T05通过6/8，产物30/60，失败原件完整保留；WorkBuddy五任务规定产物检查均通过，T04有真实请求与同一可见任务补发记录。两次WorkBuddy CLI登录错误、Codex首次T04误触发另存。共23个公开证据包：元宝原生专家模式T01为7/8、42/60；豆包云电脑T01独立重试为8/8、60/60，较早本地入口的沙盒失败0/8、0/60仍保留。元宝下载和豆包云任务的预算观察限制明确列出。两款后续各四题尚未完成覆盖，元宝T02正在运行，未计成绩。浏览器插件与系统资源不足属于采集限制，未算成产品失败。

本次交付采用[探索性分析口径](docs/exploratory-analysis-plan.md)，按实际任务复现和执行链追溯开展五产品比较。原先75次确认性实验为作者草案，公告没有规定这个次数；未实施的正式主实验成绩保持空，不追认既有预试。[后验评分审阅](reports/exploratory-score-review.md)已覆盖18次实际现场、五款产品，人工项缺证保留未知范围；已完成17/25个产品×任务组合，完整覆盖尚未完成。

阅读[书面报告](reports/report.md)和[真实预试索引](public/pilots/README.md)，复核原生交付、现场事件、失败attempt与归因边界。

## 归因原则

模型、Skill、工具权限和Harness会共同影响结果。无法把五产品换成同一模型和同一Skill时，主实验只能比较固定配置的端到端表现。研究者通过现场证据定位故障，再用同模型/同Skill的匹配对照或Harness内消融验证候选原因。没有对照的推测标为待验证，不声称已剥离模型影响。

详见[方案](docs/protocol.md)、[归因定责](docs/attribution.md)、[Harness 执行链归因补充](docs/harness-attribution-supplement.md)、[打分细则](docs/rubric.md)和[产品来源](docs/products.md)。补充方法把输入传递、请求执行、文件落地、错误反馈和状态保存作为观察主体；业务答案正确与否另记。[已实施的执行链复核](reports/harness-observations.md)逐项列出 DSH 六轮预试的写入与错误反馈对应，后续正常编辑不会被算作写入失败。官方能力介绍仅用于锁定入口，不代替实测。

## 作业材料映射

| 要求 | 材料 | 当前状态 |
|---|---|---|
| 评测方案 | docs/protocol.md、config/protocol.json、docs/exploratory-analysis-plan.md | 确认性草案未实施；本次按探索性口径复现和追溯 |
| 用例：任务、输入、完成条件 | cases/T01至T05，prompt.md、inputs、case.json | 已设计；可离线核验 |
| 表现现场 | public/pilots真实接入记录；正式封存后export至public/runs | 23个证据包；17/25个已结束的产品×任务组合，另有重试/诊断；正式0/75 |
| 赋分、标准、理由 | config/rubric.json、docs/rubric.md、reports/exploratory-score-review.json | 18次逐项审阅；缺证项与完整覆盖缺口明确 |
| 书面竞品报告 | reports/report.md、逐次公开证据与复核命令 | 真实预试报告；正式对照尚未完成 |
| 每周六个人周报邮件 | reports/weekly-template.md、reports/weekly-2026-10-17-draft.md | 仅本地模板/草稿；未发送 |
| 个人开源GitHub链接 | https://github.com/llongwang751-arch/tx-harness，MIT | 公开方案、代码、真实预试与报告 |

## 快速开始

需要Python3.11或以上，无外部Python依赖。请从仓库根目录运行：

```powershell
python -m harness_eval audit
python -m unittest discover -s tests -v
python -m harness_eval --help
```

正式实验之前，先预试并锁定版本/模型/技能条件、冻结协议。每次 `prepare` 只复制参与者可见的prompt和inputs；oracle和评分程序留在评测员目录。把workspace复制/挂载到隔离的产品目录，不让任何参评产品读这个评测仓库。

```powershell
python -m harness_eval prepare --product codex --case T01 --replicate 1 --track pilot
```

按[现场操作单](docs/collection.md)采集后，填写人工判断、封存、评分。主实验安排五产品×五任务×三次，共75个实验位。工具生成顺序、验收与汇总；scripts提供三款本地原生CLI的预试适配器，默认dry-run，显式--execute才执行，不能代替五产品实际操作或自动登录。

## 目录

```text
config/         协议、评分权重、产品入口登记
docs/           方法、归因、采集、评分与提交说明
cases/          五套任务、原始输入、仅供评测员使用的答案
harness_eval/   标准库CLI：准备、记录、核验、封存、打分、汇总
tests/          验收判定与证据门槛的回归测试
reports/        真实预试报告、周报与正式成绩草案
runs/           本地采集包（Git忽略）
public/runs/    经审查导出的公开证据包（可提交）
private/        私有原始记录（Git忽略）
```

Hash帮助复核版本与文件一致性，无法证明记录者没有造假。任务和答案公开也有记忆污染风险，因此本套任务用于过程诊断，不作模型能力通用排行榜。正式报告注明作者、采集日期、账号条件、入口、版本与研究局限。
