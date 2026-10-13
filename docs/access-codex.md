# Codex CLI 访问与预试记录

记录日期：2026-10-13。实际入口为本机官方 npm 包中的原生 `codex.exe`，版本 `codex-cli 0.159.2`，已有 ChatGPT 登录状态可用。未读取、复制或公开凭据文件。本次入口属于受控 CLI 预试，不能据此声称测过 Codex 桌面界面。

脚本默认只显示计划；`--execute` 才启动真实产品进程。给参与者的工作目录在评测仓库外，仅包含原始 `prompt.md`、用例输入和空的 `outputs/`。后续预试统一附加传输约定：`将交付文件写入 outputs/，不要修改 inputs/。` 实际提交文本另存为 `submitted-prompt.md` 并记录哈希，原用例文件保持不变。

CLI 不显式指定模型，模型标记为 `not_disclosed_clean_cli_default`，可见性为 unknown。T01 调用请求不加载用户配置与用户/项目 rules，并配置禁用项目文档、host Skill discovery、插件、hooks、memories、in-app browser 与计算机使用；内置 Skill 的真实状态未独立证明。配置中的网络禁用针对任务工具，原生模型服务仍需要通信。T01 的完整实际参数见各尝试的 launch.json。

完成 T01 后，后续 runner 另行显式禁用 apps、browser_use 与 browser_use_external，保存 runner 源文件哈希，并加入 CLI `--cd`。这些后续修正没有应用到已经完成的 T01 进程，也尚未经过新一轮真实任务验证；不能把当前脚本的全部开关回填成旧样本的条件。

## T01 的两次基础设施预试

| 尝试 | 实际结果 | 解释与置信依据 |
|---|---|---|
| attempt01 | 原生 CLI 正常结束，未产出文件。PowerShell 与 cmd 均被环境策略拒绝。 | 基础设施权限配置过窄。原始 stderr 有三次 policy rejection，最终可见消息明确说明无法读取输入。对“未产出文件”置信高；不能推断产品不能算账。 |
| attempt02 | CLI 自行读取输入、生成并验证三份文件。复核为 8/8 检查通过，产物分 60/60。 | 加入 `prefer_mxc`、工作区继承与只读官方 runtime 目录。原生命令先遇到工作目录问题，随后使用绝对路径和 `-NoProfile` 恢复。过程、产物哈希与独立 verifier 共同支持本次结果。 |

第二次尝试的 native `turn.completed` 与原字节产物均已保留。但早期脚本把 `pilot_attempt02` 用作 track，违反 evaluator 的固定枚举，导致采集终结校验失败，原始私有 `meta.json` 仍为 pending。公开精简包分别记录“原生任务完成”和“collector finalize 失败”，保留错误，不把它伪装成可封存的正式样本。未来脚本将 attempt 放在父目录，track 固定为 pilot。

首次尝试未附加输出目录后缀，第二次已附加。两次尝试属于接入修正过程，不能用来比较不同权限的效应，也不算主实验的重复次数。产物正确性只能证明这次产品配置的端到端结果；模型未知、内置 Skill 未完全可见，因此 Harness 因果归因保持 unresolved。

## 其余用例与 T04 适配限制

T02、T03、T05 的脚本路径已检查，尚未实际执行。嵌套交付文件按相对路径逐字节采集，冲突的双份输出不自动选优，输入改变会记录，预算后修改的文件会被排除。

T04 初始调用保留原生 session，其他任务使用 ephemeral 新会话。请求检测只接受原生可见 agent message，并记录原文、时间；正则结果仍需人工语义核查。两分钟内识别明确缺失汇率请求时主动补发，否则到第 120 秒被动补发。汇率文件放入参与者的输入目录后，使用原始 `thread.started` 给出的唯一 thread ID 续接，并提交统一补充消息。没有使用 `--last`。

CLI exec 每次只接收一条输入。如果首轮还在运行，适配器会终止该轮进程树再续接；此动作可能影响恢复表现，必须保留为适配器动作。它不能直接证明原生桌面的中断恢复能力。该路径尚未完成真实 T04 预试。正式实验前仍需核验 exact-thread resume、请求语义、补发时间与 Windows 工作目录行为。

原始 JSONL、stderr 和过程材料保留在 private。公开版本只保留原生已经提交的用户可见文本、工具调用/结果、状态与 usage；不公开隐藏 reasoning、系统提示、凭据或个人主目录路径。过滤规则和原文件 SHA-256 与公开文件 SHA-256 一并记录。

## 官方依据

- [CLI 参数](https://learn.chatgpt.com/docs/cli/reference)：exec、JSON 输出、ignore-user-config、ignore-rules 与 ephemeral。
- [非交互模式](https://learn.chatgpt.com/docs/non-interactive-mode)：exec 和续接方式。
- [权限配置](https://learn.chatgpt.com/docs/permissions)：命名权限、路径规则、平台边界与模型服务通信的区分。
- [Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox)：原生隔离与 `prefer_mxc`。

文档和本机 CLI help 共同用于解释入口；实际日志用于判定本机执行结果。
