# DeepSeek Harness 接入核验

核验日期：2026-10-13。本文记录接入条件、官方接口和一次真实 T01 接入预试。预试不计入正式产品排名。

## 本机已确认的状态

| 检查项 | 结果 | 依据与置信度 |
| --- | --- | --- |
| 桌面产品安装 | 已安装 DeepSeek Harness | 检查安装目录及 exe 版本信息；高 |
| 已安装版本 | `0.2.0-rc.2` | exe 的 FileVersion 与捆绑 CLI `--version` 实际输出一致；高 |
| 已安装 CLI | `resources/runtime/cli/bin/dsh.cmd` | 读取随应用分发的 launcher，实际运行了 `--version`；高 |
| PATH 入口 | 未发现 `dsh` 命令 | `Get-Command` 无匹配；只说明没有 PATH 入口，不等于未安装；高 |
| npm 全局安装 | 未发现 `@deepseek-ai/dsh` | `npm list -g` 无对应依赖；高 |
| 环境变量 | 未发现名称含 DEEPSEEK 或匹配 DSH 的变量 | 只检查名称与是否非空，未输出变量值；高 |
| 默认产品数据目录 | `~/.dsh` 存在，credential store 与 desktop profile 文件存在 | 仅做文件存在性检查，没有读取凭据、私人历史或 token；高 |
| headless profile | 已由官方 launcher 初始化 | 实际执行 headless help 和预试后存在 manifest；高 |
| 实际登录/额度 | 账户路线已成功完成一次真实任务；剩余额度未知 | `deepseek-account` 的 T01 原生执行退出码 0，并产生可解析交付；高。没有查询或购买额度 |

安装程序另有捆绑 Node、pnpm、Python 与 Office Skill 资源。因此现有桌面安装已经提供运行入口，无需为了接入再安装全局 npm 包。[官方桌面载体说明](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/apps/desktop/README.md#bundled-command-runtime)

仅执行以下不启动模型工作的版本检查：

```powershell
$dsh = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'
& $dsh --version
```

## 官方当前发布信息

2026-10-13 从 npm 官方 registry 实际查询：`latest` 和 `next` 都是 `0.2.0-rc.2`，`alpha` 为 `0.2.1-alpha.2`。本轮应固定已经安装且与 latest 一致的 `0.2.0-rc.2`；不要把 master 的新接口默认归给 rc.2。[npm 官方 metadata](https://registry.npmjs.org/@deepseek-ai%2fdsh)

- 发布 tag：`dsh-v0.2.0-rc.2`，Git commit `639ed015397290b3745d163aafe02ffee4aa3f84`。
- 下载的 master 源码快照 commit：`d743267388641bc76f17c45ce8b4c231aed1d32c`，只用于检索；接口核验使用发布 tag。
- npm metadata 保存在 `private/research/dsh-npm-metadata.json`，官方源码保存在 `private/research/dsh/`；两者均处于 gitignored 的 `private/` 中。
- 接入调查阶段没有安装全局依赖或启动模型任务。随后使用既有产品账户进行了一次预试；官方 launcher 初始化了 headless profile，评测脚本没有改写 home 或 profile 的默认配置。显式参数只通过单次 `--patch` 覆盖。

## 账户登录与 API key 两条路线

rc.2 的 base composition 包含 `deepseek-official` API-key route 和 `deepseek-account` 账户 route。前者从环境或产品 credential store 解析 `DEEPSEEK_API_KEY`；后者由产品 account service 解析登录状态，未登录时返回 `ACCOUNT_SIGN_IN_REQUIRED`，不会回退到 API key。[rc.2 base composition](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/bundle/base/cordis.patch.yml)、[账户 route](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/llm/llm-deepseek-account/README.md)

桌面与 CLI 共用同一 `DSH_HOME` 下的产品数据及 credentials，但独立管理各自 profile 的可执行包与插件。由此推断：在默认 home 中完成有效产品账户登录后，同 home 下的独立 CLI profile 可通过产品自有 credential service 使用该 grant，无需复制令牌。该共享路线有官方实现支撑；本轮真实T01账户路线请求已成功，支持本机这次登录有效，不外推其他profile或账户。[桌面与 CLI 状态共享说明](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/apps/desktop/README.md)、[账户持久化与授权边界](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/credentials/deepseek-account-platform/README.md)

实际任务使用产品 credential service 读取原有账户 grant，没有读取、打印或复制其值。账户路线的一次成功请求证明当时可用，不证明余额、未来可用性或桌面默认模型。若另用 API-key route，则由操作人在官方配置 UI 录入；仓库只保存配置名称和是否存在的事实。不要复制 token、API key 或 credential store 到评测仓库。

## 可复核的非交互入口

最短路径是现有桌面捆绑 CLI 加 `--profile headless --json`。任务可从 stdin 输入，每次不指定 `--session-id` 时创建全新持久化 session；执行进程结束后退出，不留下任务服务器。`--session-id` 用于续接已有会话，不用于第一轮人为指定一个新 ID。[rc.2 headless 接口](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/bundle/headless/README.md)

官方入口示意命令（实际预试由下述 Python runner 调用）：

```powershell
$dsh = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
# 当前目录须为该轮独立用例 workspace。
# --patch 只选本轮 route/model，不修改默认 home 的配置。
Get-Content -Raw -Encoding utf8 .\prompt.txt | & $dsh --patch .\dsh-model.patch.yml --profile headless --json -
```

账户路线的临时 patch 示例：

```yaml
- id: agent-default-model
  config:
    provider: deepseek-account
    model: deepseek-flash
    reasoningEffort: high
```

`deepseek-flash` 是 rc.2 base 配置中的模型默认值，该版本的 advisory catalog 显示名为 `DeepSeek-V41-Flash`。预试显式请求这个 ID 和 `high` effort；这记录了请求条件，不是服务端内部模型身份的独立证明。若使用 API key，把 provider 明确设为 `deepseek-official`。Desktop 选择的默认模型保存在 desktop profile，不能据此假定一个新建 headless profile 采用同一选择。[默认模型配置 contract](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/core/agent-default-model/README.md)、[rc.2 模型目录](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/llm/llm-deepseek/src/models.ts)

`--json` 输出 newline-delimited 的 `session`、`status`、`text`、`thinking`、`tool_call`、`tool_result` 和 `final` 事件。应同时封存 stdout、stderr、退出码、产物与新建 session ID。该投射只含已提交步骤，部分非最终字段有截断上限；完整持久化会话 log 才能补足过程追溯。退出码 1 或 `turn_end` 的失败原因可标识失败，不能只因为出现 `final` 就认定成功。[事件与截断规则](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/bundle/headless/README.md#machine-readable-output)

需要持续、多轮或显式初始化模型的监督程序时，使用 `--profile sdk` 的 stdio JSON-RPC：`initialize` 指定 cwd/provider/model/effort，`session/prompt` 入队任务，观察通知至 idle，最后 `shutdown`。Python 和 TypeScript SDK 是官方封装。[SDK 协议](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/sdk/protocol/README.md)、[TypeScript SDK](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/sdk/client/README.md)

Web 入口是 `dsh web --no-open`（默认 `127.0.0.1:3080`），桌面 Host 默认使用另一个端口。其 HTTP `/api` 背后是 typed Remote/Gateway 和认证/浏览器信任边界；本轮未核验一个可直接 curl 的独立任务 REST endpoint。正式自动采集优先走已文档化的 headless 或 SDK。[CLI reference](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/apps/cli/reference/README.md#web-profile)、[Remote API 层](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/api/README.md)

## 真实 T01 接入预试

使用 `scripts/run_dsh_pilot.py --execute`，在仓库外独立目录 `D:/harness-participants/pilot-dsh-T01-r1` 提供提示词、两份 CSV 和空 `outputs/`。没有提供标准答案、评分代码或其他用例。实际提交文本只在原提示词后增加交付目录约定：`将上述交付文件写入 outputs/；不要修改 inputs/。`

| 项目 | 实际记录 |
| --- | --- |
| 开始／结束 | 2026-10-13 20:29:19.737／20:30:10.948（北京时间） |
| 用时／退出 | 51.210 秒；退出码 0；没有超时 |
| Surface／版本 | 桌面捆绑 CLI，headless profile，`0.2.0-rc.2` |
| 请求模型条件 | `deepseek-account` / `deepseek-flash` / `high` |
| 单次控制项 | workspace-write；关闭 `tool-web`；排除项目和用户 Skill 根目录，保留产品捆绑 Office Skill |
| 新会话 | `session-8833d1c1-adf9-436a-bec0-2526c61c6785` |
| 事件／原生文件 | 15 次工具调用及 15 个工具结果；三个要求的文件均已交付 |
| 文件客观检查 | 8/8 通过，客观部分 60/60；仅作为预试事实，不是五产品总分 |
| 输入完整性 | 两份输入 CSV 的执行前后 SHA-256 相同；无人工修复输出 |

过程中两次 `pwsh` 返回 `SetNamedSecurityInfoW failed (Win32 5): grantWrite(workspace)`。产品调用了 `diagnose-windows-sandbox-acl` Skill，但升级命令返回 `sandbox escalation to "danger-full-access" requires approval, but no approval channel is available`。随后产品使用文件读写工具交付，并调用独立子代理复算，最终回答明确说明命令行解析校验尚未完成。评测器在产品退出后独立解析了交付文件，全部符合 T01 标准答案。

上述工具错误和审批通道缺失可由原生事件直接核验，置信度高；根因仍可能涉及 Windows ACL、当前目录权限和 headless surface，尚不能泛化到 DSH 所有安装环境。成功交付也不能仅归功于 Harness：没有同模型／同 Skill 的交叉对照，计算正确的因果归属仍是 model×Harness 联合作用。产品曾调用诊断 Skill，因此不能声称本轮完全没有 Skill 参与。

三份原生文件的 SHA-256：

- `order_ledger.csv`：`a5f28d53b9275061de7db2c4bf6cbb9306420be2138ffd2446031abd7a230d46`
- `aggregate.json`：`670fe70d9b32508b3e21119ce5118ee89d11e58b35548466e17d011cd1ee965e`
- `exceptions.json`：`4622bb1726a8bad6603a7757fe8f72f88f1baa95aacdfbd4c0668f78c4086106`

原始 stdout、收集时间戳、实际提交文本、单次配置覆盖和运行元数据保存在 gitignored 的 `private/pilots/dsh-T01-r1/`；raw stdout 含 reasoning，因此不直接公开。公开证据须删除 reasoning 和私有系统内容，并另存转换说明。事件流存在字段截断限制，不能宣称完整观察到所有后台操作。

## 真实 T04 同会话 SDK 预试

2026-10-13 使用 `scripts/run_dsh_multiturn_pilot.py --execute` 执行 SDK stdio 的两轮任务。一次 `initialize` 固定 `deepseek-account / deepseek-flash / high` 和独立 cwd；两次 `session/prompt` 使用同一新 session，第二轮 completed `turn/end` 与 `idle` 后才调用 `shutdown`。没有 kill/resume 首轮，协议收据仅证明入队，任务完成另以原生生命周期通知核验。[rc.2 SDK profile](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/bundle/sdk-app/README.md)、[SDK 方法与通知](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.0-rc.2/packages/sdk/protocol/src/types.ts)

| 阶段 | 实际现场（北京时间） |
| --- | --- |
| 初始任务 | 20:49:57.835，只提供 `trades.csv`；实际提示词附统一约定“将交付文件写入 outputs/，不要修改 inputs/。” |
| 明确主动请求 | 20:50:38.179，第 40.345 秒；原文“请提供 rates.json；缺少汇率时无法完成换算。” |
| 主动补发 | 20:50:56.231，第 58.397 秒；原 fixture SHA-256 `7d93cf6563aa57b9323cc585122e546f49aa4f458c4b52e0e40c01d3a0f9936b`；统一恢复消息 |
| 补发前产物 | 只有尚未恢复的 `incident.json`，没有最终台账或汇总 |
| 恢复完成 | 20:51:10.446；总用时 72.611 秒；正常 shutdown，exit 0；无超时或强制终止 |
| 客观检查 | 三个原生文件、7/7 检查通过，客观部分 60/60；最终金额 146636 分；仅作为预试事实 |

操作人语义复核造成请求与补发间隔 18.052 秒，虽在 120 秒内完成主动补发，仍偏离“立即补发”的理想时序，因此不把这次预试用作正式速度比较。初始 `trades.csv` 的执行前后哈希相同，没有人工改写产物。

SDK 现场出现三次 `pwsh` Windows ACL 错误和一次升级审批通道缺失。产品仍通过文件工具先记录初始阻塞，明确停止最终换算、等待汇率，随后读取补发文件并交付正确结果。这支持该环境下“请求缺失输入并在同会话恢复”的可见事实；仍不能单独归因计算正确，也不能泛化 ACL 问题。

公开材料在 `public/pilots/dsh-T04-r1/`：初始输入与补发 fixture 分开保存，实际 SDK 控制帧、收据和 running/idle 通知、81 个父会话可见事件、原生文件、7/7 检查结果与脱敏说明齐备。全量 SDK wire 中的隐藏上下文与 reasoning 留在私有目录，公开投射不含这些内容。T04 使用 SDK profile，与 T01 的 headless profile 分开标记，不混入正式 75 次统计。

后续若启动正式 DSH CLI 实验，应在冻结条件中为五个用例统一选择 SDK profile，固定账户路线、模型/effort、Sandbox 与内置 Skill 条件；不要在同一产品均分中混合 headless 与 SDK。当前仅完成接入预试，还没有据此启动正式轮次。

## 对评测的影响

headless、sdk 与桌面由不同 profile composition 启动。若评测对象定义为桌面产品，CLI 得分不能直接替代桌面得分；如采用 headless，应在报告中明确 surface、profile、内置 Skill 和模型配置，所有轮次保持一致。本次预试支持单一用例的可见行为及产物事实，还不支持五产品排名或纯 Harness 的因果优劣结论。`workspace-write` 不限制所有读取、网络和进程，脚本没有实现外部 OS 级完全隔离；这个限制必须随结果披露。
