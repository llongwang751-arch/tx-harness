# 补测公开证据定位审计

2026-10-20仓库复核发现：原导出器遗漏了6份已脱敏核查附件。四项主观察有12处引用受影响；连同额外交付/声明观察，共17处。原包不覆盖，补充公开的字节与原metadata及review内的SHA完全一致。此次补充不是重做实验，也未改判或改分。

当前核对236条evidence：包内文件定位34处、补充附件定位17处、公开event_id定位116处；结构化定位缺失0处。另有69条说明性/非结构化引用仍需人工阅读，不将其算成机器已验证的事件。

| 原实验位 | 原引用文件 / 补充公开位置 | SHA依据 |
|---|---|---|
| S02-codex-r1-allow | [evaluator-artifact-checks.json](evidence-addenda/S02-codex-r1-allow/evaluator-artifact-checks.json) | 原包metadata.raw_records_sha256及review |
| S02-codex-r1-allow | [launch-conditions-reviewed.json](evidence-addenda/S02-codex-r1-allow/launch-conditions-reviewed.json) | 原包metadata.raw_records_sha256及review |
| S02-codex-r2-allow | [artifact-review.json](evidence-addenda/S02-codex-r2-allow/artifact-review.json) | 原包metadata.raw_records_sha256及review |
| S02-codex-r2-allow | [launch-condition-projection.json](evidence-addenda/S02-codex-r2-allow/launch-condition-projection.json) | 原包metadata.raw_records_sha256及review |
| S02-codex-r2-deny | [operator-readonly-verification.json](evidence-addenda/S02-codex-r2-deny/operator-readonly-verification.json) | 原包metadata.raw_records_sha256及review |
| S02-codex-r3-deny | [external-post-exit-check.json](evidence-addenda/S02-codex-r3-deny/external-post-exit-check.json) | 原包metadata.raw_records_sha256及review |

复核：`python -X utf8 scripts/audit_contract_evidence.py --check`。逐条结果见[evidence-locators.json](evidence-locators.json)，映射和原包metadata摘要见[附件索引](evidence-addenda/index.json)。CI另核验原包manifest；此检查只验证定位与字节一致性，不能自动认可观察项的语义、现场真实性或因果结论。
