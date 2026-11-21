# T03-M 题面补充候选

已冻结。新增条款放在 T03-M 第 1 步列出 `excluded_price_changes` 字段之后。[冻结记录](freeze.md)

> 对于每条排除的价格指令，`excluded_price_changes` 中对应对象的 `reason` 必须逐字等于该条指令在 `inputs/release_directive.json` 中的 `status` 原值。保留大小写和下划线，禁止添加 `status=` 前缀或说明文字。

题面明示 `reason` 所用的输入字段，和精确 JSON 判定对齐。公告仍按题面要求保留 `正式发布：` 和其余字节。正式场使用新版本和新运行 ID 前瞻登记，按实际工作区复验权限。归因范围继续限定为产物一致性。[完整题面与样例](README.md) · [分歧与对照复算](../../reports/behavior-formal/review/T03-M-assisted-2026-11-21.md)
