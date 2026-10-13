# Codex CLI 访问与预试记录

记录日期：2026-10-13。实际入口为本机官方 npm 包中的原生 `codex.exe`，版本 `codex-cli 0.159.2`，已有 ChatGPT 登录状态可用。未读取、复制或公开凭据文件。本次入口属于受控 CLI 预试，不能据此声称测过 Codex 桌面界面。

脚本默认只显示计划；`--execute` 才启动真实产品进程。给参与者的工作目录在评测仓库外，仅包含原始 `prompt.md`、用例输入和空的 `outputs/`。后续预试统一附加传输约定：`将交付文件写入 outputs/，不要修改 inputs/。` 实际提交文本另存为 `submitted-prompt.md` 并记录哈希，原用例文件保持不变。

正式调用需要事先显式选择 `--track product_default`，且执行时协议必须已经是 `preregistered`；默认仍为 pilot，不能事后改 pilot 的 track 冒充正式样本。正式入口选项目前仅通过编译与 dry-run 检查，没有启动正式运行。

CLI 未显式指定模型。T01、T02、T03、T05 为 ephemeral 调用，标记 `not_disclosed_clean_cli_default`，可见性 unknown；不能从其它任务回推身份。T04 的 exact thread 保留了本次测试自己的原生 session，白名单 session_meta/turn_context 字段记录两轮均为 `gpt-6.1-sol`、provider 为 `openai`、CLI 为 `0.159.2`；只公开这些字段和原文件哈希，未公开整份 session、系统提示或隐藏 reasoning。这证明本次 CLI 配置的模型 ID，未独立审计服务器权重。

T01 调用请求不加载用户配置与用户/项目 rules，并配置禁用项目文档、host Skill discovery、插件、hooks、memories、in-app browser 与计算机使用；内置 Skill 的真实状态未独立证明。配置中的网络禁用针对任务工具，原生模型服务仍需要通信。各预试的完整实际参数见 launch.json。

完成 T01 后，后续 runner 另行显式禁用 apps、browser_use 与 browser_use_external，保存 runner 源文件哈希，并加入 CLI `--cd`。这些后续修正用于 T02 至 T05 的接入预试，没有应用到已经完成的 T01 进程；不能把当前脚本的全部开关回填成旧样本的条件。

## T01 的两次基础设施预试

| 尝试 | 实际结果 | 解释与置信依据 |
|---|---|---|
| attempt01 | 原生 CLI 正常结束，未产出文件。PowerShell 与 cmd 均被环境策略拒绝。 | 基础设施权限配置过窄。原始 stderr 有三次 policy rejection，最终可见消息明确说明无法读取输入。对“未产出文件”置信高；不能推断产品不能算账。 |
| attempt02 | CLI 自行读取输入、生成并验证三份文件。复核为 8/8 检查通过，产物分 60/60。 | 加入 `prefer_mxc`、工作区继承与只读官方 runtime 目录。原生命令先遇到工作目录问题，随后使用绝对路径和 `-NoProfile` 恢复。过程、产物哈希与独立 verifier 共同支持本次结果。 |

第二次尝试的 native `turn.completed` 与原字节产物均已保留。但早期脚本把 `pilot_attempt02` 用作 track，违反 evaluator 的固定枚举，导致采集终结校验失败，原始私有 `meta.json` 仍为 pending。公开精简包分别记录“原生任务完成”和“collector finalize 失败”，保留错误，不把它伪装成可封存的正式样本。未来脚本将 attempt 放在父目录，track 固定为 pilot。

首次尝试未附加输出目录后缀，第二次已附加。两次尝试属于接入修正过程，不能用来比较不同权限的效应，也不算主实验的重复次数。产物正确性只能证明这次产品配置的端到端结果；模型未知、内置 Skill 未完全可见，因此 Harness 因果归因保持 unresolved。

## 其余用例与 T04 适配限制

T02、T03、T05 各执行了一次接入预试，没有根据任务结果调参或择优。T02 产出 4 文件，7/7 检查通过，耗时 136.247216 秒；T03 产出 5 文件，6/6 检查通过，耗时 84.889195 秒，受保护文件保持原字节；T05 产出 3 文件，8/8 检查通过，耗时 101.973652 秒。三者产物分均为 60/60，初始输入哈希保持不变。私有原始记录位于 `private/codex-pilot/coverage-attempt01/`。这些预试没有正式总分，不计入主实验重复次数。

对应公开精简包为 `public/pilots/codex-T02-r1-attempt01/`、`public/pilots/codex-T03-r1-attempt01/`、`public/pilots/codex-T05-r1-attempt01/`；包含原始材料、实际传输文本、已经提交的可见原生过程、原字节产物、冻结快照、复核结果、脱敏规则与完整清单。其 ephemeral 会话没有匹配的持久模型元数据，因此模型继续保持 unknown。

嵌套交付文件按相对路径逐字节采集，冲突的双份输出不自动选优，输入改变会记录，预算后修改的文件会被排除。一次任务完成证明入口与交付格式可用，不能外推其它版本或全部重复结果。

T04 初始调用保留原生 session，其他任务使用 ephemeral 新会话。请求检测只接受原生可见 agent message，并记录原文、时间；仍需人工语义核查。两分钟内识别明确缺失汇率请求时主动补发，否则到第 120 秒被动补发。汇率文件放入参与者的输入目录后，使用原始 `thread.started` 给出的唯一 thread ID 续接，并提交统一补充消息。没有使用 `--last`。

首次 T04 预试的检测误把“若缺少汇率，会请求补充”的计划性语句当成实际请求，过早主动补发；原生模型随后也说明没有实际发出缺失输入请求。此为适配器错误，保留完整偏离证据，不计有效恢复样本。输出虽通过 7/7 检查，仍不能弥补流程协议偏离。

第二次预试收紧到句首或标点后的明确“请提供/补充/上传 rates.json/汇率文件”，并排除假设、未来请求及示例措辞。不确定含义不主动补发，不改变用例指令。原生工具列目录只见 trades.csv 后，实际消息为“请提供 rates.json；缺少汇率时无法完成换算。”请求在 23.679352 秒出现，rates 实际可用为 23.759813 秒，续接 stdin 提交为 24.399371 秒。原始与续接 thread.started ID 完全一致。总耗时 70.224178 秒，3 文件通过 7/7 校验，产物分 60/60；输入哈希保持不变。

两次 T04 的独立公开精简包位于 `public/pilots/codex-T04-r1-attempt01/` 与 `public/pilots/codex-T04-r1-attempt02/`。rates 在 releases/ 下单独表示后续补发，没有混入初始 inputs/。metadata 同时记录无效/有效触发类别、实际哈希与时序、模型白名单证据和原 thread 的续接情况。

`release-receipt.at` 是评测器开始登记/复制时传入的时间，可能早于参与者实际收到文件；补发时序采用 `initial.result.release.file_available_at`，公开 metadata 对应 `released_file.actual_available_at`。续接用户消息采用原生进程真正收到 stdin 的 `resume.result.submitted_at`，不能把更早的预写入 receipt 当成交付时刻。T02、T03、T05 没有预定补发；初始参与者文件复制完成后才登记 start 和提交任务。

CLI exec 每次只接收一条输入。如果首轮进程还在运行，适配器会终止进程树再续接。两次 T04 都发生了此动作，首轮 exit=1，续接 exit=0；首轮原生 turn.completed 已可见。这是适配器动作，不能直接证明原生桌面的中断恢复能力。正式协议需要冻结这个续接约定，并继续按原始过程核验实际请求与恢复。即使显式加入 --cd，Windows 工具首轮仍遇到相对路径落在 C:\ 的问题，模型随后自行使用绝对路径恢复；没有人工修复文件。

原始 JSONL、stderr 和过程材料保留在 private。公开版本只保留原生已经提交的用户可见文本、工具调用/结果、状态与 usage；不公开隐藏 reasoning、系统提示、凭据或个人主目录路径。过滤规则和原文件 SHA-256 与公开文件 SHA-256 一并记录。

## 官方依据

- [CLI 参数](https://learn.chatgpt.com/docs/cli/reference)：exec、JSON 输出、ignore-user-config、ignore-rules 与 ephemeral。
- [非交互模式](https://learn.chatgpt.com/docs/non-interactive-mode)：exec 和续接方式。
- [权限配置](https://learn.chatgpt.com/docs/permissions)：命名权限、路径规则、平台边界与模型服务通信的区分。
- [Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox)：原生隔离与 `prefer_mxc`。

文档和本机 CLI help 共同用于解释入口；实际日志用于判定本机执行结果。
