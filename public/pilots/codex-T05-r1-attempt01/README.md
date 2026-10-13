# Codex T05 单次接入预试

真实原生 CLI 生成 3 份交付文件，独立确定性校验 8/8 通过，产物分 60/60。属于单次接入预试，正式总分为空，不计入 75 个正式实验位。没有调优用例、手动修改产物或择优重试。

prompt.md 与 inputs/ 是原始用例材料，submitted-prompt.md 为实际 stdin 文本，附加统一输出目录约定；outputs/ 保持产品生成的原始字节。原生已经提交的可见文本与工具结果经白名单过滤及用户主目录脱敏。没有公开隐藏 reasoning、系统提示、Skill 正文或凭据。哈希与过滤规则见 provenance.json。

模型只依据本次自己的原生会话收据披露；ephemeral 无匹配持久会话元数据时保持 unknown，不能从 T04 回推。产物正确性置信依据为原字节文件与 verifier；Harness 因果归因保持 unresolved。

复核命令：

```powershell
python -m harness_eval verify --case T05 --outputs public/pilots/codex-T05-r1-attempt01/outputs
```
