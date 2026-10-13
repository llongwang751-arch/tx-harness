# DSH SDK 五任务接入预检

2026-10-13，DSH 的 T01、T02、T03、T05 各补做一次原生 SDK 预检，与先前的 SDK T04 共同覆盖五个任务。所有尝试均保留；没有重试选优、修复产品输出或计入正式实验。本页不合成产品总分，不给出五产品排名。

| 任务 | 原生文件的确定性检查 | objective 文件分 /60 | 记录耗时 | 公开证据 | 额外观察 |
|---|---:|---:|---:|---|---|
| T01 | 8/8 | 60 | 36.721 秒 | [dsh-sdk-T01-r1](../public/pilots/dsh-sdk-T01-r1/README.md) | shell 权限错误，文件工具完成交付 |
| T02 | 7/7 | 60 | 33.154 秒 | [dsh-sdk-T02-r1](../public/pilots/dsh-sdk-T02-r1/README.md) | shell 权限错误，文件工具完成交付 |
| T03 | 6/6 | 60 | 135.945 秒 | [dsh-sdk-T03-r1](../public/pilots/dsh-sdk-T03-r1/README.md) | protected.txt 原字节通过，但交付目录有 9 个探针残留 |
| T04 | 7/7 | 60 | 72.611 秒 | [dsh-T04-r1](../public/pilots/dsh-T04-r1/README.md) | 原生 SDK 同会话补发；主动请求后观察员有 18.052 秒补发延迟 |
| T05 | 6/8 | 30 | 17.441 秒 | [dsh-sdk-T05-r1](../public/pilots/dsh-sdk-T05-r1/README.md) | 逐单金额与金额汇总失败，来源审计声明及订单范围检查通过 |

四个新任务在同一账户并发启动，组名 `sdk-coverage-20261013`，最多 4 个。T04 先前单独运行。上述耗时包含共享服务、账户和本机资源的并发影响，不能用于单任务速度比较。任务完成的判断来自原生父会话 `turn/end`、`idle`、SDK 正常 `shutdown` 与 exit 0；四项无超时、无强杀。消息队列的 `messageId` 只用于证明提交受理，不当作任务完成证据。

五项共同的显式条件为 DSH `0.2.0-rc.2` 桌面捆绑 CLI、原生 JSON-RPC SDK/profile，`deepseek-account / deepseek-flash / high` 请求，`workspace-write`，默认用户/项目 Skill roots 关闭、产品 Office Skill 保留、web 工具关闭。模型后端未被独立证明，新包明确写 `requested-not-attested`。诊断 Skill 仍可使用，全局 home/profile 默认组合未完全排除；这些事实不足以成立纯 Harness 因果比较。`workspace-write` 和关闭 web 工具也不证明读权限、进程或网络隔离。

T03 的 6/6 只覆盖用例规定的六项文件条件。产品为了解决 shell 不可用时的字节保真问题，创建了 9 个编码探针；删除命令被原生权限机制拒绝，文件原样留在公开包中。不能把 objective 满分写成整洁交付或无缺陷。

T05 的错误可直接由原始文件复核：`B001.net_cents` 为 `10200`，冻结标准答案为 `8200`；汇总 `gross_cents=32555`，应为 `22555`；`net_cents=28599`，应为 `18599`。错误值在真实 `write` 调用、回读与最终文件中一致出现，随后助手的正确性声明与文件不符。公开的 [artifact-differences.json](../public/pilots/dsh-sdk-T05-r1/artifact-differences.json) 列出差值；[deterministic-verification.json](../public/pilots/dsh-sdk-T05-r1/deterministic-verification.json) 保留两项失败。以上判断对文件事实的置信为高；对模型、Skill、Harness 各自应承担多少责任，仍为未隔离。不能将金额失败直接归因于注入执行，也不能由来源审计声明通过推断完整网络隔离或普遍注入抵抗能力。

进一步追溯公开 `tool/call`：错误数值在 `write` 请求的 `content` 中已经存在，不是只在产品最终回答中出现。台账请求 `call_00_hwB98YnopBR78Y1EjMwR0662` 见 [visible-events.jsonl 第22行](../public/pilots/dsh-sdk-T05-r1/visible-events.jsonl#L22)（原 stdout 第40行），其中 B001 的 net 已为 10200；第23行对应同一 callId 的 completed 结果。汇总请求 `call_01_HyLU5fZePenO0t7aqcnr1149` 见 [第24行](../public/pilots/dsh-sdk-T05-r1/visible-events.jsonl#L24)（原 stdout 第42行），其中 gross 已为 32555、net 已为 28599；第25行对应 completed 结果。请求内容的 UTF-8 字节分别与最后台账和汇总逐字节一致，SHA-256 如下。

| 原生 write 请求及最终文件 | 请求 content 与最终文件共有 SHA-256 |
|---|---|
| invoice_ledger.csv | `4bd14adcf668018d274866f38e1f77446cd03c4ecd365615fcebcff0c00a504b` |
| summary.json | `5f6fcf24199399a07e94f4de5c3f54bfeda6bd428b799aa0b00eed0385e9d791` |

可复核事实分为两层：对“错误已存在于公开工具请求”的置信为高，对“文件执行保存了相同请求字节”的置信也为高，依据是请求、结果、原文件和 manifest 的交叉核验。这定位到可见请求与文件执行的边界，不能识别请求生成前的责任：原生 `tool/call` 不独立证明后端模型的未加工输出，未开展同模型、同 Skill 的 Harness 替换或消融实验。模型算术、Skill 影响、Harness 请求组装及环境错误后的策略选择仍不可单独定责。公开第46行（原 stdout 第67行）中助手声称逐单 `10200+5199+5200=28599`，该算术声明与实际和 `20599` 不符；它是可见自述，不能当作另一次计算工具执行。

新采集入口为 [run_dsh_sdk_pilot.py](../scripts/run_dsh_sdk_pilot.py)，默认只打印配置，需要 `--execute` 才真实运行；任务参数为 `--case T01..T05`。新目录统一用 `dsh-sdk-Txx-rN`，已有目录拒绝覆盖。旧 T04 runner、原始 outputs 与可见事件保留；提示词记录语义已公开纠错并补充发送 receipt。旧 runner SHA-256 为 `0b2899b87a456df40cb72fd5130667ceec73e00354e4d85f05939d8224fbcb34`。新包的 `adapter-source/` 保存执行前采集代码及共享函数快照，元数据记录实际哈希。它们使用相同 SDK 协议与显式条件，但采集代码版本和串并发安排不同；正式实验仍需先冻结一个版本并统一运行安排。

[export_dsh_sdk_pilot.py](../scripts/export_dsh_sdk_pilot.py) 导出原字节 inputs/outputs、原始题目、实际发送 prompt、工具和文本投影、SDK 控制回执、独立文件检查和 manifest。公开投影仅包含父会话可见已提交文本、真实工具调用/结果与生命周期状态；产品 Skill 正文删去、本机路径匿名化，隐藏推理、系统内容、认证信息、请求上下文、原始 stdout/stderr 和子会话内部事件保留在私有区。T03 的父会话 subagent 调用/结果可见，不能据此把未公开的子会话内部过程当作完整现场。

公开材料由执行代理逐项审阅，未声称外部人工审计。四包的 manifest 全量匹配，公开输入与原生工作区输入字节一致，公开输出与原生工作区输出字节一致；`verify_public_pilots.py` 重新计算得到 8/8、7/7、6/6、6/8 和对应 60、60、60、30 文件分。各包 `claims.json` 逐项给出依据、置信范围和归因限制。哈希支持复核文件完整性，不能单独证明私有采集真实性。

发送记录已做公开纠错：最初的四项本地导出及此前的 SDK T04 误将 Windows CRLF 磁盘记录的 SHA 标为实际发送文本 SHA，现从真实发送的 `session/prompt` 单一文本块重建 UTF-8 原字节（LF），保留原记录文件、旧误标值和纠错说明。四新包使用 `prompt.md` 保存实际内容、`prompt-recorded-file.md` 保存记录文件；T04 保留原 `prompt.md`，新增 `wire-prompt.md` 和 `wire-supplement-prompt.md`。各包 `transmission-receipt.json` 支持逐字节复核，哈希范围为解码后的文本内容，不是整个 JSON-RPC 封包。原生 outputs、visible-events 和检查结果未改变。旧 headless T01 只读检查确认记录文件为 CRLF，但没有独立捕获的出站 stdin 字节日志，不能以当前代码推断其实际字节哈希；暂按记录文件证据理解。
