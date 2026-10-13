# Codex T01 接入预试 attempt01

这是实际原生 CLI 执行的公开精简材料。属于接入预试，不能作为正式 75 个实验位中的样本或五产品排名依据。

第一次尝试因采集器的权限配置阻止 shell 启动，未产生交付文件；记基础设施问题，不给产品能力打零分。

prompt.md 和 inputs/ 为原始材料；submitted-prompt.md 是实际 stdin 传输文本；outputs/ 保持产品生成的原始字节。verification.json 可用仓库 verifier 复算。原生日志经白名单过滤和用户主目录路径脱敏，原文件哈希与过滤说明见 provenance.json。

复核命令：

```powershell
python -m harness_eval verify --case T01 --outputs public/pilots/codex-T01-r1-attempt01/outputs
```
