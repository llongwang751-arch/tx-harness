# Codex T04 接入预试 attempt02

第二次预试在原生工具列出只有 trades.csv 后，观察到明确『请提供 rates.json』请求；按协议补发，并用同一 thread ID 继续任务。

两次均为真实原生 CLI 执行，三份产物均通过 7/7 确定性校验，产物分 60/60；正式总分为空，不进入 75 个正式实验位。

初始输入仅为 inputs/trades.csv，rates.json 在 releases/ 下表示后续补发。补发文件原哈希、实际可用时间、请求原文、续接 stdin 时间及同一 thread ID 核验见 metadata.json 和 evidence/。

适配器在补发后 kill 首轮原生进程再 exec resume，必须与原生桌面恢复能力区分。原生 session_meta/turn_context 的白名单字段表明两轮配置模型为 gpt-6.1-sol，provider=openai；系统提示、隐藏 reasoning 与凭据均未公开。

outputs/ 均为产品生成的原字节文件。公开日志只保留已提交可见事件，并脱敏用户主目录路径；原 private 文件哈希及过滤规则见 provenance.json。

复核命令：

```powershell
python -m harness_eval verify --case T04 --outputs public/pilots/codex-T04-r1-attempt02/outputs
```
