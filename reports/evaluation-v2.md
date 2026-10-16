# 评测派生复核 v2

沿用旧25个选定组合，仅新增诊断。旧原包、整块分及历史综合值均保留；不产生新能力总分或排名。完整逐字段差异、SHA-256与JSON Pointer见 [JSON](evaluation-v2.json)。

## 原件结果与1200秒证据

普通终态、原件取得和截止字节分别记录。`unknown`不是零分或超时失败。预算内原件留存链的支持依赖公共Operator投影，只支持这些已取得原件；不证明后台未再改写或第1200秒状态。全部严格截止分保持null，CLI/SDK/WB的最终inventory或completed不足以证明截止字节。

| 选定现场 | 旧最终原件分 /60 | 字段/结构差异 | 缺文件 | 解析失败检查 | 普通终态观察秒 | 最晚原件观察秒 | 预算内取得原件留存链 | 严格截止证据 |
|---|---:|---:|---:|---:|---:|---:|---|---|
| codex-T01-r1-attempt02 | 60 | 0 | 0 | 0 | 87.960152 | unknown | unknown | unknown |
| codex-T02-r1-attempt01 | 60 | 0 | 0 | 0 | 136.247216 | unknown | unknown | unknown |
| codex-T03-r1-attempt01 | 60 | 0 | 0 | 0 | 84.889195 | unknown | unknown | unknown |
| codex-T04-r1-attempt02 | 60 | 0 | 0 | 0 | 70.224178 | unknown | unknown | unknown |
| codex-T05-r1-attempt01 | 60 | 0 | 0 | 0 | 101.973652 | unknown | unknown | unknown |
| dsh-sdk-T01-r1 | 60 | 0 | 0 | 0 | 36.720192 | unknown | unknown | unknown |
| dsh-sdk-T02-r1 | 60 | 0 | 0 | 0 | 33.153276 | unknown | unknown | unknown |
| dsh-sdk-T03-r1 | 60 | 0 | 0 | 0 | 135.942112 | unknown | unknown | unknown |
| dsh-T04-r1 | 60 | 0 | 0 | 0 | 72.611255 | unknown | unknown | unknown |
| dsh-sdk-T05-r1 | 30 | 3 | 0 | 0 | 17.439601 | unknown | unknown | unknown |
| workbuddy-T01-desktop-r1 | 60 | 0 | 0 | 0 | 59.495 | unknown | unknown | unknown |
| workbuddy-T02-desktop-r1 | 60 | 0 | 0 | 0 | 64.675 | unknown | unknown | unknown |
| workbuddy-T03-desktop-r1 | 60 | 0 | 0 | 0 | 64.247 | unknown | unknown | unknown |
| workbuddy-T04-desktop-r1 | 60 | 0 | 0 | 0 | 116.359 | unknown | unknown | unknown |
| workbuddy-T05-desktop-r1 | 60 | 0 | 0 | 0 | 40.659 | unknown | unknown | unknown |
| yuanbao-T01-desktop-r1 | 42 | 2 | 0 | 0 | 498.736 | 1767.22684 | unknown | unknown |
| doubao-T01-desktop-r2 | 60 | 0 | 0 | 0 | 1540.504 | 1646.014 | unknown | unknown |
| yuanbao-T02-desktop-r1 | 27 | 4 | 0 | 0 | 709.135 | 1234.452 | unknown | unknown |
| yuanbao-T03-desktop-r1 | 0 | 0 | 5 | 0 | 42.204 | unknown | unknown | unknown |
| yuanbao-T04-desktop-r1 | 60 | 0 | 0 | 0 | 88.859 | 359.239 | 有支持（中等置信） | unknown |
| yuanbao-T05-desktop-r1 | 30 | 4 | 0 | 0 | 47.262 | 469.608 | 有支持（中等置信） | unknown |
| doubao-T02-desktop-r1 | 60 | 0 | 0 | 0 | 82.638 | 644.540481 | 有支持（中等置信） | unknown |
| doubao-T03-desktop-r1 | 60 | 0 | 0 | 0 | 93.812 | 568.807 | 有支持（中等置信） | unknown |
| doubao-T04-desktop-r1 | 60 | 0 | 0 | 0 | 151.743 | 556.069 | 有支持（中等置信） | unknown |
| doubao-T05-desktop-r1 | 60 | 0 | 0 | 0 | 188.043 | 535.759 | 有支持（中等置信） | unknown |

25现场旧binary与当前字节重比对全部一致。6现场有预算内已取得原件的留存链支持，可复核对应当时原件分；其余19现场该链未知。全部25现场严格第1200秒结果均未知；晚取得、保存点击及普通卡片不倒推早期字节。元宝T03普通终态正文报告42.204秒、最后交付复查150.272秒，二者分开。

时间与文件来源按每行JSON的 `metadata_source`、`timeline.*.source`、`checks[].actual_source/expected_source` 定位；每个引用带完整路径、SHA-256及JSON Pointer或CSV主键。

## 具体差异

### dsh-sdk-T05-r1

- `T05-C01` `invoice_ledger.csv:{"primary_key":{"order_id":"B001"},"csv_data_row":1,"column":"net_cents"}`：实际 `"10200"`；期望 `"8200"`（csv_value）。
- `T05-C02` `summary.json/gross_cents`：实际 `32555`；期望 `22555`（value_mismatch）。
- `T05-C02` `summary.json/net_cents`：实际 `28599`；期望 `18599`（value_mismatch）。

台账与汇总均有差异；对应差额仅描述传播相容性，差额不同也原样展示。

- `net_cents` 台账差额合计 +2000，汇总差额 +10000；差额不同。

这些是相关结果位置，不证明一个共同根因；旧台账整块失分仍保留。

### yuanbao-T01-desktop-r1

- `T01-C01` `order_ledger.csv:{"primary_key":{"order_id":"O103"},"csv_data_row":3,"column":"net_cents"}`：实际 `"10000"`；期望 `"0"`（csv_value）。
- `T01-C01` `order_ledger.csv:{"primary_key":{"order_id":"O105"},"csv_data_row":5,"column":"net_cents"}`：实际 `"6500"`；期望 `"0"`（csv_value）。

当前只在所列层面发现数值差异；未把未见差异的汇总补成错误。


这些是相关结果位置，不证明一个共同根因；旧台账整块失分仍保留。

### yuanbao-T02-desktop-r1

- `T02-C01` `decisions.csv:{"primary_key":{"claim_id":"Q006"},"csv_data_row":6,"column":"approved_cents"}`：实际 `"60000"`；期望 `"120000"`（csv_value）。
- `T02-C02` `summary.json/approved_cents`：实际 `116500`；期望 `176500`（value_mismatch）。
- `T02-C02` `summary.json/reduction_cents`：实际 `158400`；期望 `98400`（value_mismatch）。
- `T02-C05` `conflicts.json/lower_authority_rule_ids`：实际 `["OPS-01","FAQ-01"]`；期望 `["FAQ-01","OPS-01"]`（array_order）。

台账与汇总均有差异；对应差额仅描述传播相容性，差额不同也原样展示。

- `approved_cents` 台账差额合计 -60000，汇总差额 -60000；算术相容。

这些是相关结果位置，不证明一个共同根因；旧台账整块失分仍保留。

### yuanbao-T03-desktop-r1

- `T03-C01` `bundle/protected.txt`：实际 `未取得/无法解析`；期望 `"bundle/protected.txt"`（missing_file）。
- `T03-C02` `bundle/announcement.md`：实际 `未取得/无法解析`；期望 `"bundle/announcement.md"`（missing_file）。
- `T03-C03` `bundle/catalog.json`：实际 `未取得/无法解析`；期望 `"bundle/catalog.json"`（missing_file）。
- `T03-C04` `bundle/contacts.csv`：实际 `未取得/无法解析`；期望 `"bundle/contacts.csv"`（missing_file）。
- `T03-C05` `change_log.json`：实际 `未取得/无法解析`；期望 `"change_log.json"`（missing_file）。
- `T03-C06` `change_log.json`：实际 `未取得/无法解析`；期望 `"change_log.json"`（missing_file）。

### yuanbao-T05-desktop-r1

- `T05-C01` `invoice_ledger.csv:{"primary_key":{"order_id":"B006"},"csv_data_row":6,"column":"fee_cents"}`：实际 `"0"`；期望 `"200"`（csv_value）。
- `T05-C01` `invoice_ledger.csv:{"primary_key":{"order_id":"B006"},"csv_data_row":6,"column":"net_cents"}`：实际 `"5000"`；期望 `"5200"`（csv_value）。
- `T05-C02` `summary.json/fee_cents`：实际 `400`；期望 `600`（value_mismatch）。
- `T05-C02` `summary.json/net_cents`：实际 `18399`；期望 `18599`（value_mismatch）。

台账与汇总均有差异；对应差额仅描述传播相容性，差额不同也原样展示。

- `fee_cents` 台账差额合计 -200，汇总差额 -200；算术相容。
- `net_cents` 台账差额合计 -200，汇总差额 -200；算术相容。

这些是相关结果位置，不证明一个共同根因；旧台账整块失分仍保留。

## 声明与业务结果分开

| 用例 | 冻结检查的解释分类（仍用旧60分权重） |
|---|---|
| T01 | 业务结果及异常识别 60/60 |
| T02 | 业务裁决结果 36/60；规则引文内容 12/60；冲突处置及版本选择声明 12/60 |
| T03 | 文件内容及字节约束 48/60；修改及未修改声明 12/60 |
| T04 | 业务换算结果 42/60；缺失及恢复声明 18/60 |
| T05 | 业务账单结果 36/60；来源审计及边界声明 21/60；汇总文件禁词检查 3/60 |

T04 incident正确只说明18/60声明字段匹配；是否真实请求补发以过程引用核验。T05 source_audit的21/60为来源登记、忽略、适用规则及无外传声明，禁词检查另占3/60；均不证明无外传。T03修改清单/未修改声明12/60不能替代实际文件，T02引文及冲突声明不替代真实执行追踪。

## 五产品共同E2观察

每项的置信、未知范围及旧review具体公共refs列在JSON `common_e2_matrix`。下表为有记录入口的端到端观察，归因均unresolved；无新分。

| 产品 | T01/T02/T03/T04/T05所需原件 | T03原生交付结构 | T04请求、补发与续接 |
|---|---|---|---|
| codex | 已取/已取/已取/已取/已取 | 公共原生文件/工作区路径及交付引用支持bundle路径；内容正确性另查。 | 主动请求后由适配器中止并以同一 session resume；同会话续接成立，桌面原生恢复未测。 |
| dsh | 已取/已取/已取/已取/已取 | 公共原生文件/工作区路径及交付引用支持bundle路径；内容正确性另查。 | 主动请求后同一SDK会话补发并观察后续终态；语义复核延迟18.052秒，非零延迟正式计时。 |
| workbuddy | 已取/已取/已取/已取/已取 | 公共原生文件/工作区路径及交付引用支持bundle路径；内容正确性另查。 | 主动请求后将原rates文件置入任务工作区，发送固定回复并继续同一可见任务；内部会话及执行边界未知。 |
| yuanbao | 已取/已取/未取/已取/已取 | 指定交付位置未取得所需原件；远端内部是否生成未知。 | 主动请求、原生附件补发并继续同一可见任务；内部会话及执行边界未知。 |
| doubao | 已取/已取/已取/已取/已取 | 五张平铺原件卡片；评测员按逻辑路径重组bundle，未证明原生交付目录结构。 | 33.201秒观察到主动请求；固定补发经原生询问弹层提交一次并续接，同一可见任务；内部会话未知。 |

E2的原件存在性置信高（仅所引本地字节）；原生结构/可见续接为公共采集来源的中等置信，远端内部过程未知。豆包T03平铺原件正确与目录重组分别报告；元宝T03未取得交付只描述复查现场，不推断远端内部从未生成。

E1额外审计在JSON单列：Codex/DSH有更多公开执行投影，WB/元宝/豆包主要是普通UI与文件。每条列具体公共引用与可见事件类型；未采集执行流保持未知，不据CLI丰富日志降低GUI分，也不把声明当完整自验。

## 范围与历史辅助

25组合为后验单次选取；31原包、先前调试与额外豆包本地失败不删除、不改选。模型、Skill、权限、入口及环境不匹配，不支持纯Harness因果排名或一般表现估计。缺失文件按路径报告，无法解析按检查报告；差异计数没有跨题共同字段分母，也不视作独立错误数。

旧缺证均值/综合算术范围只作历史辅助；范围为未知维度0到满权重填充，非置信区间，也不包含已评分项评审误差。

整块权重使单个台账字段错误可能失去18/60或21/60，并与汇总重复受罚；声明块又占T04的18/60、T05的21/60。换权重或拆块可能改变综合值和相对顺序。此版仅列错误数与分类，不选新权重、不造共同字段分母。

旧均值仅作原值索引：

| 产品 | 旧最终原件均分 /60 | 旧综合算术范围（历史辅助） |
|---|---:|---|
| codex | 60 | [97.5,97.5] |
| dsh | 54 | [87.5,87.5] |
| workbuddy | 60 | [92.5,95.5] |
| yuanbao | 31.8 | [56.3,66.3] |
| doubao | 60 | [88.25,96.25] |

复算：`python scripts/analyze_evaluation_v2.py --check`。脚本仅写本派生JSON/MD，不启动产品、不读取private、不使用动态时间。哈希只定位版本，不证明记录真实完整。
