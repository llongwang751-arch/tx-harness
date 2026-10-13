# WorkBuddy T01 入口诊断预试

这是实际安装 CLI 的一次独立执行记录，不计正式样本。未读认证值、未修复产品输出。

普通回答与原生结果都要求 `/login`，且结果标记 `is_error=true`。没有工具调用和产品交付文件。退出码为0不能证明任务成功；本次任务得分留空。

只允许的结论：当前独立 headless 入口未获得可用认证。置信依据为保存的普通消息与结果事件。桌面登录状态、实际底模、Skills 和任务执行能力无法由本次证明。

`manifest.json` 可复核包内文件SHA256；`metadata.json` 记录原始与实际prompt哈希、输入哈希及实际UTC起止时间。原始流保存在本地private目录；公开流已去除系统事件、隐藏推理、认证字段、用户路径及会话标识。

复现：安装相同版本后运行 `python scripts/run_workbuddy_pilot.py --case T01 --replicate <fresh-number> --setting-sources none --execute`。认证状态可能不同，不能保证同样报错。
