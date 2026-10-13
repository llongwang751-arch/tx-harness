# 公开证据转换说明

本包是 2026-10-13 的一次真实 DSH T01 接入预试，不进入正式 75 次样本的分母，也不构成桌面 UI 表现或纯 Harness 因果结论。

`outputs/`、`inputs/` 与提示词磁盘记录 `prompt.md` 均逐字节复制；`prompt.md` 含 CRLF。此前误称它为实际提交文本，现明确它不能证明精确出站 stdin 字节：没有独立的 outbound stdin 捕获，实际发送字节 SHA-256 为 unknown/null，不推断 LF，也不以当前代码回填。文件 SHA-256 与执行收集的元数据一致。公开元数据中的私有源文件摘要用于关联原始记录，摘要本身不能证明现场真实性。原始文件留在 gitignored 的 private/pilots/dsh-T01-r1；没有公开 raw stdout。

过滤规则：

- 从原生 stdout JSONL 删除所有 8 个 thinking 事件，未读取/公开持久化会话中的系统提示或私人历史。
- 保留 session、status、committed text、final、实际 tool_call 和实际 tool_result。没有根据产品自述补造工具调用。
- 一个 Skill 结果的指令正文被省略，保留其实际调用、完成状态和原始正文 SHA-256。其余保留内容经过操作人逐项敏感信息审查。
- 用户主目录路径（含 Windows 8.3 短名）统一替换为 C:/Users/<user>；相应公开事件不再与原始事件字节相同。参与者 workspace 路径和 fixture 内容保留。
- 每个公开事件保留真实收集时间和原始 stdout 行号；收集时间不是产品内部发生时间。headless 投射可能有字段截断，未观察到的后台活动不作推断。
- 不公开凭据、隐藏推理、私人系统内容或其他用户会话。模型后端身份与剩余额度仍未知。

`deterministic-verification.json` 由仓库真实检查器对本包原生 outputs 独立生成：8/8 检查通过。artifact 检查支持交付正确；助手和子代理关于“独立校验”的文字属于产品主张。15 次工具调用、三次 pwsh 错误和 read/write 交付则有原生投射支持。
