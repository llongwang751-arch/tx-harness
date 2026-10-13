# WorkBuddy 本机入口核对

核对日期：2026-10-13。此文记录安装元数据、入口探测和两次真实 T01 入口预试；没有读取历史聊天或输出认证值。原始事件流保存在忽略提交的 `private/` 下，不直接发布。

## 安装与进程证据

| 项目 | 本机证据 | 结论 |
|---|---|---|
| 桌面程序 | `E:\workbuddy\WorkBuddy.exe` 的 ProductVersion / FileVersion | `5.7.7.0` / `5.7.7` |
| 桌面包 | `E:\workbuddy\resources\app.asar` 内 `package.json` | 包名 `@genie/workbuddy-desktop`，版本 `5.7.7`，主入口 `main/index.js` |
| 内置 CLI | `E:\workbuddy\resources\app.asar.unpacked\cli\package.json` | 包名 `@genie/agent-cli`；发布元数据 `@tencent-ai/codebuddy-code` / `2.156.0`；普通入口 `bin/codebuddy` |
| 产品配置 | 同目录 `product.json` 的四个限定元数据字段 | `productName=WorkBuddy`、`applicationName=WorkBuddy`、`dataFolderName=.workbuddy`、`genieVersion=5.7.7` |
| 内置运行时 | WorkBuddy 子进程的 ExecutablePath（用户路径脱敏） | `%USERPROFILE%\.workbuddy\binaries\node\versions\22.22.2-6\node.exe` |
| 打包形态 | CLI 的 `dist` 目录 | 存在 `codebuddy-headless.js` 和 `codebuddy-lite-wb.mjs`；入口依据 `-p`、`--acp`、格式参数等选择 headless |

首次核对时 WorkBuddy 主进程 PID 为 `24700`，监听端口 `18488`；子进程 PID `15656` 监听 `63128`、`63145`。这些只是一次进程快照，重启后会变化；执行预试时主 PID 已变为 `13868`。`18488/ping` 的首次只读 HTTP 请求在绕过系统代理后返回 `404`，所以不能把这个端口当作评测 API。

## 可继续验证的普通入口

本机已有系统 Node 与 WorkBuddy 内置 Node，不必重新安装软件。建议先用内置运行时确认帮助，再在独立用例目录运行内置 CLI：

```powershell
$wbNode = Join-Path $env:USERPROFILE '.workbuddy\binaries\node\versions\22.22.2-6\node.exe'
$wbCli = 'E:\workbuddy\resources\app.asar.unpacked\cli\bin\codebuddy'
& $wbNode $wbCli --version
& $wbNode $wbCli --help
```

官方 CodeBuddy 文档提供 `-p/--print` 无头执行、`--input-format` / `--output-format`、`--allowedTools` 等参数。内置脚本也识别 `--acp`。正式任务应先以帮助确认此安装版本支持的参数，再用冻结方案指定的权限、模型、工作目录和独立会话；只记录普通回答、工具事件与产物。

内置 CLI 使用 WorkBuddy 产品配置；本次独立入口未获得可用登录，实测见下。它是否继承桌面模型选择、插件和权限策略仍未确认。不能仅凭共享组件认定 CLI 与桌面 UI 表现等价；若用 CLI 采集，应在报告中明确入口，并先与桌面端做相同提示的预试。

## 真实 T01 入口预试

由 `scripts/run_workbuddy_pilot.py` 调用安装的 CLI，进程隐藏运行，任务目录放在评测仓库之外：`D:/harness-participants/pilot-workbuddy-T01-r1` 和 `pilot-workbuddy-T01-r2`。起始目录仅有原始 prompt、两份 CSV 输入与空 `outputs/`。实际提交内容在原始 prompt 后追加共同传输说明“将交付文件写入 outputs/，不要修改 inputs/。”，原始及实际提交 SHA256 各自保存。

两次都请求新的独立 session、`--print --verbose --output-format stream-json --no-session-persistence`；未传 `--model`，请求模型为产品 `auto`。请求仅开放 Read / Write / Edit / Glob / Grep，使用显式空 MCP 与 `--strict-mcp-config`，过程设置请求禁用 hooks，权限模式为 `acceptEdits`。限制和入口都属于预试适配条件：本轮没有验证操作系统沙箱，不能把受限文件工具与正常桌面任务工具等同。

| 私有证据目录 | 设置来源 | 真实开始时间（UTC） | 耗时 | 普通回答及结果事件 |
|---|---|---|---|---|
| `private/pilots/workbuddy-T01-r1` | `none` | 2026-10-13 12:29:20 | 3.96 秒 | 要求 `/login`；`result.is_error=true`、`error_during_execution` |
| `private/pilots/workbuddy-T01-r2` | 原生 `user,project,local` | 2026-10-13 12:30:43 | 3.04 秒 | 同样要求 `/login`；`result.is_error=true`、`error_during_execution` |

两次原样普通回答是 `Authentication required. Please use /login command to sign in to your account`；没有工具调用、没有任何交付文件，输入和 prompt 哈希未变。虽然 CLI 进程退出码均为 0，结果事件已明确错误，不能把退出码 0 判为任务成功。第二次恢复正常设置来源后仍报认证要求，支持“本次独立 headless 入口未获得可用登录”的有限结论；它不证明桌面账户未登录，也不证明产品不会完成 T01。此结论的置信依据是两个保存的普通回答及结果事件，实际底模、工具执行能力和 Harness 任务表现仍不可评。

启动元数据只显示 `model=auto`，无法据此认定底层模型。其 `tools` 字段列出包括 Bash / Skill / WebSearch 在内的完整列表，与请求子集不一致；缺少调用时无法证明限制的有效执行。原始流包含启动信息，必须经过人工脱敏与隐藏内容过滤后才能公开。以上预试不计入正式样本，不给产品打零分，也不纳入竞品排名。

后续可使用桌面正常任务入口完成同一输入预试，或通过 CLI 自身正常 `/login` 流程完成登录；不应手工提取桌面认证值、伪造回答或注入完成事件。

来源：[官方 CLI 参考](https://www.codebuddy.cn/docs/cli/cli-reference)、[官方无头模式](https://www.codebuddy.ai/docs/zh/cli/headless)、[官方 v2.143.0 发布说明](https://www.codebuddy.ai/docs/cli/release-notes/v2.143.0)。发布说明明确介绍 WorkBuddy 精简构建 `codebuddy-lite-wb`。网页索引可读，直接抓取页面本次超时；安装版本以本机证据为准。

## 不应误用的入口

安装包的 `main/eval-inject-server.js` 定义过 `EvalProxyServer`：默认端口 `18485`，普通接口包含 `POST /sessions`（`cwd`、可选 `mode` / `model`）和 `POST /chat/{sessionId}`（`prompt`）。然而当前 `main/index.js` 的启动管线把相关 `evalModeEnabled` 参数写为 `false`，没有证据表明该服务正在运行。不能把源码中存在的服务记成已可用入口。

该创建接口会设置 `permissionMode=bypassPermissions`；若日后启用，也必须作为权限变量记录。`/sessions/{id}/inject` 会直接插入用户、助手和工具回合，不能用它生成表现现场证据。

`%USERPROFILE%\.workbuddy\wbipc\endpoint.json` 存在，包含 named-pipe 端点与认证 ticket；只确认存在，未输出值。已安装的 `resources\plugins\workbuddy-builtin\skills\library\workbuddy_ipc\__init__.py` 是标准库 IPC 客户端，公开 `connect`、`get_pipe`、`invoke` 原语，用于技能的宿主能力请求。未连接或调用，因其并非已核验的普通会话执行入口。存在 ticket 不能证明模型服务已经登录可用。

`resources\wb-guest-sdk\wb.js` 的 guest bridge 存在 `sendPrompt`、`runPrompt`、`requests` 等会话方法，但它依赖桌面 renderer 的 `window.__wbInvoke` 通道；仅凭方法名称不能从外部直接调用，也没有在本次核对中控制 UI。
