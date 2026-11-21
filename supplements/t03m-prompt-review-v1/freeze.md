# T03-M 新版 C01、C06 冻结记录

2026-11-21 冻结新版规则。技术复核人确认两项均能仅凭新版题面判断，8 个正反例复算一致。[独立复核回执](../../reports/behavior-formal/review/T03-M-independent-rule-review-2026-11-21.md)

| 冻结对象 | 版本 |
|---|---|
| 完整题面、样例定义、样例回执 | `6dea9eb464c8b9ed86411554dfb85d6e23d3b848`，[固定资料](https://github.com/llongwang751-arch/tx-harness/tree/6dea9eb464c8b9ed86411554dfb85d6e23d3b848/supplements/t03m-prompt-review-v1) |
| 完整题面 SHA-256 | `c04f8b7832caffa9b45c3b52ce0c86bd3d49e527a4e68b97d1a36c8931638dc8` |
| 判卷器及规则 | `a6bb1d21d3d93535b32636c04a6473631757f835`，用 `python scripts/audit_t03m_prompt_review.py --check` 在固定快照中复算 |

C01 按原始 `status` 字符串逐字核对。C06 只允许替换正式发布时刻，其余字节保留。这次冻结覆盖新题面与两项判定。正式投递仍需收回旧版盲判、前瞻登记新版运行，并在实际工作区重新验证输入与评分资产权限。[正式场状态](../../reports/behavior-formal/codex-t03m-readiness.md)
