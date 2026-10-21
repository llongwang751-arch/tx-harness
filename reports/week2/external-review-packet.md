# 两条结论的外部复核包

作者：李明远。准备日期：2026-10-21。当前状态：材料已准备，尚未收到外部复算记录。本文件与CI都不是外部独立复核。请实际完成后在独立反馈中记日期、结论和发现；此处不预填评审人或结果。

## 结论一：不合规CSV被旧判卷器接受的原因

主张范围：N6仅缺闭引号，旧宽松解析与预期字段相等；严格守卫可以区分该反例与合法无末尾换行的P2。

1. 阅读[T03原任务](../../cases/T03/prompt.md)、[N6反例原件](../../public/grader-audit-v3/N6/outputs/bundle/contacts.csv)和[P2合法对照](../../public/grader-audit-v3/P2/outputs/bundle/contacts.csv)。检查完整文件，不能只看网页自动补行的显示。
2. 运行`python -X utf8 scripts/audit_grader_v3.py --check`。在[审计数据](../grader-audit-v3.json)中核对N6旧版接受、新版拒绝，P2新版接受；定位N6的开关行，确认只关闭CSV_STRICT就重新接受，其余文件SHA相同。
3. 对照[旧解析器](../../harness_eval/core.py)和[新守卫](../../evaluation_v3/grader.py)，判断是否真能把原因限定到该解析路径。记录任何不同Python环境下的差异，不把22个期望通过说成普遍正确。

完成条件：反馈包含实际执行命令、Python版本、日期、N6/P2结果及是否同意该局部原因；若无法执行则只记录未完成。

## 结论二：S02的许可行为只支持指定记录条件

主张范围：三组允许/拒绝臂有真实目标尝试和对应状态；条件核对仅支持已记录参数匹配，未鉴定后台模型或五产品因果优劣。

1. 运行`python -X utf8 scripts/verify_contracts_v2.py --check`和`python -X utf8 scripts/analyze_permission_pairs_v2.py --check`，核对[实际配置表](../permission-pairs-v2.json)。
2. 至少逐项阅读[r2允许臂](../../public/supplements/contracts-v2/S02-codex-r2-allow/review.json)与[r2拒绝臂](../../public/supplements/contracts-v2/S02-codex-r2-deny/review.json)，在同目录visible-events.jsonl按event_id找到目标写入请求和结果；再查看允许臂原件及[拒绝后只读核查](../../public/supplements/contracts-v2/evidence-addenda/S02-codex-r2-deny/operator-readonly-verification.json)。
3. 运行`python -X utf8 scripts/audit_contract_evidence.py --check`，确认附件能追到原SHA。检查“没有文件”是否被单独当成许可通过，是否将后台条件误写为已完全统一。

完成条件：反馈指出实际核对的配对、事件和文件，给出同意/异议及证据位置。若仅看CI结果或本页说明，不能登记为完成现场复核。

## 反馈记录格式

- 评审者及实际日期：由评审者填写。
- 检出的仓库commit、Python和操作系统：由评审者填写。
- 结论一实际结果、证据及异议：由评审者填写。
- 结论二实际结果、证据及异议：由评审者填写。
- 未能完成的步骤及原因：由评审者填写。

没有反馈时保持U04未完成，不代写评审意见。实际个人联系方式不要求公开；如需匿名公开，由评审者自行确认。
