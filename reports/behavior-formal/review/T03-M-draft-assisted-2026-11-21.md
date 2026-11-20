# T03-M 新版题面辅助复核

2026-11-21。回执署名为 Codex，角色为辅助复核，声明本会话未参与判卷器实现。回执说明此前已看过旧版结果，本次重新核对和复算。新版材料取自 `6dea9eb`，旧版材料取自 `a6bb1d2`。[新版题面](https://github.com/llongwang751-arch/tx-harness/blob/6dea9eb464c8b9ed86411554dfb85d6e23d3b848/supplements/t03m-prompt-review-v1/prompt.md) · [旧版抽查资料](https://github.com/llongwang751-arch/tx-harness/tree/a6bb1d21d3d93535b32636c04a6473631757f835)

| 检查 | 辅助复核意见 |
|---|---|
| 新版 C01 | 第 1 步明确要求 `reason` 逐字等于输入里的 `status` 原值。加 `status=`、说明文字或字符串内多余的空格应失败。只调整 JSON 排版或对象键顺序应通过 |
| 新版 C06 | 只删除「正式发布：」标签，即使时间正确，也违反保留其余字节的要求 |
| 旧版 C01 | 按旧题面判断通过。P-B 已排除，旧题面未规定 `reason` 的精确写法。按冻结判卷复算为失败 |
| 旧版 C06 | 按旧题面和冻结判卷均为失败 |

回执的冻结意见为同意采用新版，理由是新增条款消除了 C01 的题面分歧，C06 的样例符合原要求。仓库维护侧再次执行两条复算，新版 8 个样例与预期一致，两个正例各 60/60，六个反例各 51/60。旧版原件两项判卷均失败，历史分 42/60。[新版复算数据](../../../supplements/t03m-prompt-review-v1/results.json) · [旧版复算数据](../../../public/behavior-formal/t03m-assisted-review-2026-11-21.json)

新版仍等待符合条件的人确认题面及样例，旧版独立盲判待回收。正式冻结与业务题投递保留待办。[独立复核材料](../../../supplements/t03m-prompt-review-v1/README.md) · [正式场状态](../codex-t03m-readiness.md)
