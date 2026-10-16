# 提交与复核

本次按公告允许的任务复现与过程追溯路径交付。五产品各五题的当前实际覆盖见[报告](../reports/report.md)和[后验评分](../reports/exploratory-score-review.json)；准备目录不算已测试。原75次确认性实验是作者提出的后续草案，不是公告规定的提交次数，不追认本次预试。

2026-10-16另在首次执行前登记21个固定文件契约及许可配对实验位，材料和判定规则见[补测协议](../supplements/contracts-v2/protocol.json)，实际封存结果与分母见[补测索引](../public/supplements/contracts-v2/README.md)。这批补测与原五题分开统计；它减少部分任务语义干扰，仍不证明五产品使用同一模型部署或内置Skill。

1. 提交个人公开仓库：[llongwang751-arch/tx-harness](https://github.com/llongwang751-arch/tx-harness)，使用分支`codex/evaluation`并记录实际提交commit。
2. 阅读[分析口径](exploratory-analysis-plan.md)、[五套用例](../cases)、[打分细则](rubric.md)和[证据索引](../public/pilots/README.md)。报告逐题结果须与原件、检查和人工理由对应。
3. 按索引复核指定原件及manifest；评分JSON每项保留来源SHA-256、定位、置信依据、替代解释和归因。失败、诊断、重试与协议偏离全部保留。
4. 分开报告端到端正确性与Harness执行边界。模型、Skill、权限未匹配时不发布纯Harness因果排名；E2界面标签不补成内部工具调用。
5. 明确单人非盲审阅、不同入口和计时精度、采集中断、预算后取回与缺证项。未知为null，范围是算术展开，不是统计置信区间。

公开包只含经精确审阅的任务片段、原件和来源收据。账号、其他会话、私有路径、签名URL、隐藏推理及Skill正文不公开。哈希支持定位和改动检查，不能独立证明来源真实性。避免需要登录才能访问的临时证据链接。

```powershell
python -X utf8 -m harness_eval audit
python -X utf8 scripts/verify_public_pilots.py
python -X utf8 scripts/audit_harness_observations.py
python -X utf8 scripts/analyze_evaluation_v2.py --check
python -X utf8 scripts/verify_contracts_v2.py --check
python -X utf8 scripts/analyze_permission_pairs_v2.py --check
python -X utf8 -m unittest discover -s tests -v
```

若另做75次确认性实验，应先统一条件、冻结新的预注册commit，再执行随机计划；它属于另一个研究批次，不修改当前封存包或给既有现场倒填预注册状态。

周六周报应含本周进展、难点突破、下周计划。当前保存[2026-10-17邮件草稿](../reports/weekly-2026-10-17-draft.md)，用户暂不处理邮件发送；没有发送邮件或建立自动任务。
