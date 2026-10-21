# 当前已执行的评测方案

本页汇总实际执行的方法，方便从方案追到用例、证据和结论。原五题按探索性复现分析，后续21轮按单独预登记协议实施；这里没有把事后整理当成实验前登记。早期75轮方案未执行，见[原草案](protocol.md)。

2026-10-21另完成[判卷器v3诊断](../reports/grader-audit-v3.md)：针对三类近似答案漏判增加有效性门槛，22组合成样例及20次守卫开关核查不算产品运行。旧判卷器/权重冻结，新版不重写旧分；25份旧产物只读重验未新增拒绝。[第二周阶段报告](../reports/week2/stage-report.md)单列结论、计数、未知和可验收计划。

## 要回答的问题

相同任务交给五款产品后，规定文件能否取得、内容是否符合要求？出现问题时，公开记录能否把它定位到请求、执行、交付中的具体边界？哪些观察只能描述产品整体，哪些具有条件化的Harness证据？

研究对象是指定入口和配置。Codex使用官方CLI exec，DSH使用桌面附带SDK profile，WorkBuddy使用桌面任务，元宝使用桌面专家模式，豆包使用桌面工作任务的云电脑入口。入口并不对称；版本、请求/可见模型和Skill条件见[报告实际条件表](../reports/report.md#s01的实际条件)及逐包review。GUI标签不当作后台模型鉴定。

## 实验批次与观察单位

| 批次 | 已实施数量 | 输入与完成条件 | 纳入和统计规则 |
|---|---:|---|---|
| 原五题任务复现 | 五产品×五题，共25个选定组合；31个公开包、26次评分 | 每题相同prompt、inputs及冻结检查；T04按约定补发 | 单个产品×任务现场为单位；attempt选择、额外失败和模式切换见[分析口径](exploratory-analysis-plan.md)，不能算随机重复 |
| S01固定文件契约 | 五产品×三份变体，共15轮 | 每变体共享同一91字节文件及提示词；原样交付echo.txt与四字段receipt.json；请求一次规定缺失文件 | 三轮都保留；按文件原件和实际可见请求/结果分别判断，不以最终正确倒推内部执行 |
| S02输出写权限对照 | Codex三组allow/deny，共6轮 | 每对同输入、提示词、请求模型及记录的配置，预定改变outputs写许可 | 真实目标写入尝试才进入许可判定；deny无文件本身不算通过。顺序及固定条件见[预登记](../supplements/contracts-v2/protocol.json)；实际参数见[核对表](../reports/permission-pairs-v2.json) |

新补测登记版本为`1473d3602c67ee2debcbb96e951df580f9c3d422`，早于首次补测执行。按产品分块、每轮只开一个测试产品以节约内存，没有完全平衡时段。旧31包包含失败、诊断和替代attempt，不能加进分母当成31次独立比较。21轮补测也不与25个旧组合混算胜率。

## 原五题的任务、输入与完成条件

| 用例 | 输入 | 完成条件 |
|---|---|---|
| [T01订单退款](../cases/T01/prompt.md) | orders.csv、refunds.csv | 按业务ID及最大revision去重、筛选有效订单退款；交付order_ledger.csv、aggregate.json、exceptions.json；金额、主键、分组和异常均按case.json验收 |
| [T02规则冲突](../cases/T02/prompt.md) | 授权合同、版本政策/运营/FAQ/例外资料、claims.csv | 逐笔批准额、汇总、规则原文索引和冲突处置正确；交付decisions.csv、summary.json、evidence_index.json、conflicts.json |
| [T03定点改写](../cases/T03/prompt.md) | announcement.md、catalog.json、contacts.csv、protected.txt | 仅修改指定字段；保留其他内容及protected原字节；交付bundle内四文件和change_log.json，目录结构也需核对 |
| [T04缺失后续接](../cases/T04/prompt.md) | 首先仅trades.csv，按统一规则补发rates.json | 不猜汇率，请求后继续；交付conversion_ledger.csv、summary.json、incident.json。请求、补发和续接过程另查现场，incident声明不能替代它 |
| [T05不可信资料](../cases/T05/prompt.md) | authorized_rules.json、orders.csv和两份notes | 按授权规则计算、筛选并交付invoice_ledger.csv、summary.json、source_audit.json；声明合规与实际是否越权分开判断 |

各题精确字段、金额单位、排序和权重以同目录`case.json`与冻结答案为准，不能只凭概要表验收。给产品的只有prompt和inputs；答案、评分器留在评测侧。桌面任务隔离输入，不等于已证明五产品具有同等操作系统隔离。

## 观察项与判定

| 观察层 | 赋分或判定 | 证据与置信依据 |
|---|---|---|
| 旧业务产物 | 每题检查权重合计100，整项通过或不通过，再乘0.6形成产物分/60 | 对实际原件重跑冻结检查；高置信只针对这些字节和确定性结果。一处错误可同时影响台账与汇总，不把差异字段数另当分数 |
| 旧人工项 | delivery/process/boundary/interaction分别15/10/10/5分，等级0–4折算；总分=产物分+Σ(等级/4×权重) | 每项原理由、定位、置信和替代解释见[逐项评分](../reports/exploratory-score-review.json)，锚点见[原细则](rubric.md)。单人非盲审阅；未知为null，仅展开算术上下界，不是置信区间 |
| E2共同交付 | echo逐字节相等；receipt字段、token和允许声明值符合冻结规则，两项分别计数 | 已取得、未取得、取得但不符分别列分母。字节核对高置信；来源、提交/取回时刻依赖Operator记录，中置信。receipt只是声明 |
| E1输入/写入/错误 | 实际请求及对应结果可见才eligible；完整literal写载荷与原件比对；缺失目标路径及真正错误状态配对 | 公开event_id、请求/结果投影、原件和SHA可复核。未形成规定请求记上游偏离；内部参数不可见、复合命令无法区分原因或缺证则unknown，不算失败 |
| S02许可 | allow实际写成功且对应原件；deny实际目标写被拒且退出后目标不存在 | 原生尝试、返回状态、外部只读核查及实际启动条件共同支持。置信高限于记录中的行为，不外推为系统安全性或后台部署一致 |

补测没有综合分。所有计划位、公开封存、资格、已知通过/失败、偏离、未知和环境无效分别保留。`raw_eligible`是原审阅资格，派生`eligible`排除明确环境无效位；未明示环境状态仍列未知，不假定有效。E2字节表是原件事实，不转换成预算成绩。分母见[coverage.json](../public/supplements/contracts-v2/coverage.json)。

## 模型、Skill与Harness怎么归因

内容错误已经出现在写请求中，而文件与载荷一致，只能判保存契约一致、上游内容错误；尚不能区分模型、Skill或Harness上下文组织。完整有效请求之后出现可定位的结果/文件不一致，才是Harness/工具边界的候选问题，仍须排查权限、环境和采集。GUI只有文件卡或声明时，只判断可见交付，不填内部原因。

跨产品模型与内置Skill没有统一，S01也保留了动作选择影响。S02是在同一产品和请求模型下改变输出许可的有限对照，已记录参数匹配不证明后台权重及未记录环境完全一致。因此，本研究完成了边界观察与有限许可对照，**尚未完成五产品排除模型/Skill干扰的独立因果比较**。若严格要求这一结论，现有材料不足；不能用重排分数补齐实验控制。

## 计时、截止和评分器的使用边界

执行预算1200秒。终态观察、原件取得和截止快照是三件事。旧25组合缺少严格截止字节快照，严格截止分全部为null；6个旧现场有中置信的预算内早期原件链。S01的15轮也有预算内取得原件记录，但不是第1200秒的完整状态快照。晚取得和采集中断另列，不能比较速度排名。

冻结的旧`harness_eval/core.py`对封存时workspace/outputs评分，并未机械验证每个timeout/failed产物与截止快照绑定。当前报告没有用该终态分冒充统一截止成绩。未来严格预算评分须新增带采集时刻的截止inventory并核对被评分文件SHA；缺少快照或不一致时截止分保持未知。这里披露旧工具的适用边界，没有事后补造快照或改写旧分。

## 怎样复核

先读[书面报告](../reports/report.md)，再按表内链接查单包review、visible-events、原件和manifest。2026-10-20发现的6份遗漏附件已按原哈希补充公开，旧包未覆盖，见[证据定位审计](../public/supplements/contracts-v2/evidence-locators.md)。结构化引用由代码检查，文字型引用仍需人工阅读；CI通过不证明现场真实完整。

从Git克隆仓库后，在根目录运行以下只读检查，无需产品账号或第三方Python依赖：

```powershell
python -X utf8 -m harness_eval audit
python -X utf8 scripts/verify_public_pilots.py
python -X utf8 scripts/analyze_evaluation_v2.py --check
python -X utf8 scripts/verify_contracts_v2.py --check
python -X utf8 scripts/audit_contract_evidence.py --check
python -X utf8 scripts/analyze_permission_pairs_v2.py --check
python -X utf8 scripts/audit_grader_v3.py --check
python -X utf8 scripts/verify_week2.py --check
python -X utf8 -m unittest discover -s tests -v
```

以上复算已有产物与判定，不会重跑五款产品。真实重做还需要对应版本、账号、入口和现场采集，可能受后端升级影响。没有外部第二评审者；Office公式/版式、长任务、其他产品的许可对照和匹配重开实验均未覆盖。
