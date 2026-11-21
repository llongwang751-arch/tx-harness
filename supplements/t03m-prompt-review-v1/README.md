# T03-M 新版题面与判卷样例

**新版规则已冻结。** 完整题面在第 1 步增加一条 `reason` 约定。对每个排除条目，`reason` 逐字取对应指令的原始 `status`。其他交付项沿用原题面。[新版完整题面](prompt.md) · [冻结记录](freeze.md)

## 正反例

每个样例都从固定提交的完整参考产物复制一份。表里的差异是该例的唯一改动。用固定提交的判卷器运行后得到下列结果。[参考产物](https://github.com/llongwang751-arch/tx-harness/tree/a6bb1d21d3d93535b32636c04a6473631757f835/supplements/behavior-protocol-v1/reference-outputs/T03-M) · [样例定义](examples.json) · [机器复算](results.json)

| 样例 | C01 指令分流 | C06 发布公告 | 产物分 |
|---|---|---|---:|
| 完整参考产物，P-B 的 `reason` 为 `draft_do_not_apply` | 通过 | 通过 | 60/60 |
| 同一 JSON 内容，只压缩排版并重排对象键 | 通过 | 通过 | 60/60 |
| `reason` 写成 `status=draft_do_not_apply` | 失败 | 通过 | 51/60 |
| `reason` 写成 `draft_do_not_apply（草稿）` | 失败 | 通过 | 51/60 |
| `reason` 写成 `apply` | 失败 | 通过 | 51/60 |
| `reason` 末尾多一个空格 | 失败 | 通过 | 51/60 |
| 省略 `reason` | 失败 | 通过 | 51/60 |
| 只删公告中的 `正式发布：` 标签，保留时间 | 通过 | 失败 | 51/60 |

```text
python scripts/audit_t03m_prompt_review.py --check
```

## 复核回传

请未参与判卷器实现的人先阅读新版题面，确认能否仅凭题面决定上述写法是否合规，再核对样例与复算。回传署名和角色、复核日期、资料提交或 `results.json` 里的题面 SHA-256、C01 约定是否明确、C06 样例是否判得对，以及接受冻结或建议修改的意见。历史产物的独立抽查仍按原操作单完成。[历史抽查操作单](../../reports/week6/judge-spot-check.md)
