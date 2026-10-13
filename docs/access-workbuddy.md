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

后续优先使用桌面正常任务入口完成同一输入预试。当前捆绑包不具备可直接使用的交互 `/login` 入口，详见下节；不应手工提取桌面认证值、伪造回答或注入完成事件。

来源：[官方 CLI 参考](https://www.codebuddy.cn/docs/cli/cli-reference)、[官方无头模式](https://www.codebuddy.ai/docs/zh/cli/headless)、[官方 v2.143.0 发布说明](https://www.codebuddy.ai/docs/cli/release-notes/v2.143.0)。发布说明明确介绍 WorkBuddy 精简构建 `codebuddy-lite-wb`。网页索引可读，直接抓取页面本次超时；安装版本以本机证据为准。

## 不应误用的入口

安装包的 `main/eval-inject-server.js` 定义过 `EvalProxyServer`：默认端口 `18485`，普通接口包含 `POST /sessions`（`cwd`、可选 `mode` / `model`）和 `POST /chat/{sessionId}`（`prompt`）。然而当前 `main/index.js` 的启动管线把相关 `evalModeEnabled` 参数写为 `false`，没有证据表明该服务正在运行。不能把源码中存在的服务记成已可用入口。

该创建接口会设置 `permissionMode=bypassPermissions`；若日后启用，也必须作为权限变量记录。`/sessions/{id}/inject` 会直接插入用户、助手和工具回合，不能用它生成表现现场证据。

`%USERPROFILE%\.workbuddy\wbipc\endpoint.json` 存在，包含 named-pipe 端点与认证 ticket；只确认存在，未输出值。已安装的 `resources\plugins\workbuddy-builtin\skills\library\workbuddy_ipc\__init__.py` 是标准库 IPC 客户端，公开 `connect`、`get_pipe`、`invoke` 原语，用于技能的宿主能力请求。未连接或调用，因其并非已核验的普通会话执行入口。存在 ticket 不能证明模型服务已经登录可用。

`resources\wb-guest-sdk\wb.js` 的 guest bridge 存在 `sendPrompt`、`runPrompt`、`requests` 等会话方法，但它依赖桌面 renderer 的 `window.__wbInvoke` 通道；仅凭方法名称不能从外部直接调用，也没有在本次核对中控制 UI。

## 用户需要的最小正常登录操作

2026-10-13 再次只读核对后，应使用 WorkBuddy 桌面端登录，不要求用户导出 Cookie、token 或 API key，也不要求为了登录购买额度。内置 CLI 的认证错误不能说明桌面账号已退出登录。

本机已安装客户端，用户可在 PowerShell 中运行以下命令打开它，也可点击现有 WorkBuddy 快捷方式：

```powershell
& 'E:\workbuddy\WorkBuddy.exe'
```

若客户端已经显示账户头像且可新建任务，保持该状态即可；无需重新登录。若显示登录按钮，点击后浏览器会打开 WorkBuddy 官方登录页。在页面弹窗勾选服务协议与隐私政策，用自己的微信扫码完成登录；也支持手机号、邮箱和 SSO。页面显示登录成功后，返回客户端，停在空白的新任务界面。以上流程来自 [WorkBuddy 官方 Windows 登录说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Installation-Win-Guide#登录)，是账号认证步骤，不是账单或订阅操作。

用户需要完成的只有其本人账号的正常扫码/验证码/SSO 认证，并让桌面新任务界面可用。后续任务输入、证据采集和产物核验由评测者完成；实际自动控制仍须单独验证，不以“用户已登录”代替已完成采集。

### 为什么不提供当前内置 CLI 的 `/login` 命令

[通用 CodeBuddy 官方快速入门](https://www.codebuddy.ai/docs/cli/quickstart)描述了交互 CLI 启动后选择登录渠道并打开浏览器，[slash commands 文档](https://www.codebuddy.ai/docs/cli/slash-commands)列出 `/login`。这是通用 CodeBuddy Code 文档，不能直接当作当前 WorkBuddy 精简捆绑包的可用入口。

只读安装证据显示：当前 `bin/codebuddy` 在未指定非交互参数时加载 `dist/codebuddy.js`，而本机包只有 `dist/codebuddy-headless.js` 与 `dist/codebuddy-lite-wb.mjs`，没有 `dist/codebuddy.js`。`dist/web-ui/index.html` 也不存在。因此“直接运行内置 CLI，再输入 `/login`”不是本机已验证的可执行步骤。前述预试错误中的 `/login` 仅是普通认证错误文案，不证明相应界面存在。

headless 安装源码具有 `/api/v1/auth/account/login` 与认证管理器代码，但没有核验它是当前桌面宿主正在提供的普通会话接口，也没有发现官方文档支持将现有桌面登录无值导出地迁入这个独立入口。单凭源码存在方法不能视为已可调用的宿主服务。没有读取或复制运行中进程认证值，没有调用该接口，也没有启动替代登录服务器。

如果后续改用单独安装的完整 CodeBuddy Code 完成 CLI 登录，产品入口、认证路线与设置都已改变；应作为另一个明确配置的受控实验，不能把它的结果直接替代 WorkBuddy 桌面成绩。
