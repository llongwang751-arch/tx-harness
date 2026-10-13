# DSH T04 真实多轮接入预试

桌面捆绑 CLI `0.2.0-rc.2` 的 SDK profile，请求 deepseek-account / deepseek-flash / high。一个 runtime、同一 session，经官方 initialize / session/prompt / shutdown 协议执行两轮，没有 kill/resume 首轮。

主动请求缺失汇率后补发，最终三个原生文件，7/7 客观检查通过（客观部分 60/60）。总用时 72.611 秒包含 18.052 秒操作人复核等待；补发前只有故障记录，无最终台账或汇总。命令工具再次出现 Windows ACL 与无审批通道错误，文件工具仍完成交付。

- [可见原生事件](visible-events.jsonl)
- [SDK 发出的控制帧](sdk-sent.jsonl)
- [原生 SDK 收据与 running/idle 通知](sdk-control-events.jsonl)
- [原始用例提示词](case-prompt.md) 与 [实际提交文本](prompt.md)
- [初次缺失输入请求](initial-request.md)
- [补发时间和 fixture hash](release.json)
- [最终原生回答](final-response.md)
- [运行条件和收据](run-metadata.json)
- [确定性产物检查](deterministic-verification.json)
- [判断、置信依据与替代解释](claims.json)
- [过滤与局限](redaction.md)

这是独立 SDK pilot；不计正式 75 次样本，不替代桌面产品得分。
