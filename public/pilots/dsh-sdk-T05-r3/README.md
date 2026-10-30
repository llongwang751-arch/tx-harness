# DSH T05 SDK 接入预检（一次真实执行）

这是独立的新 SDK 预检包，不计入正式实验分母，不产生五产品排名或 Harness 因果得分。原生输出未修复，失败和额外文件均保留。

冻结文件检查结果为 **8/8，objective 60.0/60**。详情见 `deterministic-verification.json`；每项主张的范围、依据与局限见 `claims.json`。

SDK `initialize`、单次 `session/prompt` 与 `shutdown` 使用一进程、一新会话。`messageId` 只表示消息已入队，另有同一父会话 `turn/end`、`idle` 及正常退出记录。没有操纵 GUI，没有超时强杀、人工输出修复或重试选优。原始输入、原始题目 `case-prompt.md`、实际发送内容 UTF-8 字节 `prompt.md`、磁盘记录原字节 `prompt-recorded-file.md` 分开保存。`transmission-receipt.json` 从真正发送的 SDK 文本块复核内容哈希；Windows 磁盘记录含 CRLF，而实际传输为 LF，哈希不代表整个 JSON-RPC 封包。

四项 T01/T02/T03/T05 在同一账户并发启动（group `sdk-coverage-20261013`，最多 4 个）。记录耗时包含并发资源和服务影响，不能用于单任务速度比较。旧 T04 先前单独执行；两次采集代码哈希及共享函数快照公开，但不据此宣称串并发是相同处理。

显式请求 `deepseek-account / deepseek-flash / high`，模型可见性 `requested-not-attested`。统一 SDK/profile、`workspace-write`、默认用户/项目 Skill roots 关闭、产品 Office Skill 保留、web 工具关闭。诊断 Skill 仍可存在。`workspace-write` 不证明读权限、进程或网络隔离；全局 home/profile 可能还有默认组合。

`visible-events.jsonl` 仅发布父会话已提交可见文本、实际工具调用/结果和 turn/step 状态。Skill 正文已删，个人路径匿名化。SDK 回执另经字段白名单过滤；隐藏推理、系统提示、请求上下文、认证、原始 stdout/stderr 和子会话内部事件均不公开。工具调用以原生 `tool/call` 事件为证据，助手自述不当作调用。`projection-receipt.json` 列过滤计数；私有原始材料仅发布 SHA-256，哈希不能单独证明采集真实性。

`adapter-source/` 是执行前保存的实际采集代码及依赖快照。`one-run-overlay.redacted.yml` 的安装路径是占位符，实际 overlay 哈希见元数据。公开材料由执行代理逐项敏感内容审阅，未声称外部人工审计。
