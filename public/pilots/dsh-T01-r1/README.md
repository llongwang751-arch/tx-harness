# DSH T01 真实接入预试

版本 0.2.0-rc.2，桌面捆绑 CLI 的 headless profile。请求 deepseek-account / deepseek-flash / high，51.210 秒，exit 0，原生交付三份文件，8/8 客观检查通过。

两次 pwsh 调用因 Windows ACL 错误失败，升级请求因 headless 没有审批通道被拒绝。产品以文件读写工具和子代理完成并披露命令行校验限制。没有人工修复产物。该事实仅适用于当前 surface、配置和本机环境。

- [原生可见事件](visible-events.jsonl)
- [运行条件与摘要](run-metadata.json)
- [原磁盘提示词记录（CRLF）](prompt.md)
- [最终原生回答](final-response.md)
- [客观检查](deterministic-verification.json)
- [过滤与公开局限](redaction.md)

不计正式产品排名；无法把正确计算或失败根因单独归给模型、Skill 或 Harness。

提示词证据纠错：此前把 `prompt.md` 称为“实际提交文本”；它实际是 Windows CRLF 磁盘记录。未独立捕获出站 stdin 字节，实际发送字节 hash 为 unknown/null；不推断它是 LF，也不由当前代码重建。记录文件、原生 outputs 和可见事件原字节保留，旧标注及此前 manifest hash 见 [纠错收据](transmission-correction-receipt.json)。
