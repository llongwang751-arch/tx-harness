# Harness 执行边界的探索性观察

此表由已脱敏的真实公开证据独立生成。没有读取private原始流、修改产品产物或追认正式实验。这些是操作实例的对应检查；每个公开包只是一轮episode，工具调用数量不是独立重复数。不提供纯Harness分或五产品排名。

| Episode | 写入公开载荷与最终文件匹配 | 可比写入分母 | 未知/被覆盖 | 真实错误文本对应error状态 | 可配对错误分母 |
|---|---:|---:|---:|---:|---:|
| [dsh-sdk-T01-r1](../public/pilots/dsh-sdk-T01-r1) | 3 | 3 | 0/0 | 4 | 4 |
| [dsh-sdk-T02-r1](../public/pilots/dsh-sdk-T02-r1) | 4 | 4 | 0/0 | 2 | 2 |
| [dsh-sdk-T03-r1](../public/pilots/dsh-sdk-T03-r1) | 13 | 13 | 0/1 | 7 | 7 |
| [dsh-sdk-T05-r1](../public/pilots/dsh-sdk-T05-r1) | 3 | 3 | 0/0 | 2 | 2 |
| [dsh-T01-r1](../public/pilots/dsh-T01-r1) | 3 | 3 | 0/0 | 3 | 3 |
| [dsh-T04-r1](../public/pilots/dsh-T04-r1) | 3 | 3 | 0/1 | 4 | 4 |

已审计 6 个探索性episode；没有把多条工具调用合并成更多独立样本。

写入分母：明确outputs目标的完成write，公开内容为字符串、请求/结果唯一对应、最终文件存在，且没有同目标的后续或重叠write/edit。按UTF-8编码公开请求内容，与最终文件原字节逐项计算SHA256。写入后有唯一配对且完成的write/edit，单列superseded并引用后续操作；后续/重叠操作失败、未完成或配对不明确，记unknown，不把工具报错当作未修改文件的证明。缺字段、目标无法对应或缺文件也记unknown。未重建shell、子会话或不可见修改，数值仅描述公开投射与最终快照是否一致，不证明最后一次实际写入。

错误反馈分母：原生工具结果文本以Error:开头，且能用同一请求ID唯一对应先前实际请求。检查独立的status字段是否为error。无真实错误文本的成功调用不进入该分母；无法配对仍记unknown。

置信高只针对可复核的字节一致或字段对应事实。差异不能自动归为Harness错误；日志截断、后续修改、路径映射或工具实现仍需检查。错误来源和后续恢复选择不能由这些指标定责。

未覆盖的模型语义、Skill内容、状态持久化、实际执行参数、权限实现以及其他产品链路保持未知，不记0。本脚本目前只适配DSH公开可见事件；其余产品不因未适配而判失败。

详细实例、公开事件行号、调用ID、载荷和文件哈希见harness-observations.json。manifest支持包内完整性，不单独证明来源真实性。

复核命令：

```powershell
python -X utf8 scripts/audit_harness_observations.py
```
