# WorkBuddy T01 原生桌面预试

2026-10-13 在正常登录的 WorkBuddy 5.7.7 桌面新任务中真实执行 T01。起始隔离目录只有题目、两份CSV及空outputs，没有oracle；提交原题加共同outputs交付说明后，没有追问或修复产物。

可见模型选择器为 Deepseek-V4.1-Flash，权限为“允许完全访问”，账户edition为free。首次采集到完成界面距发送动作前时间戳 **59.495秒**；这是观察区间上界，精确服务完成时刻未知。

三份原生文件通过 **8/8** 独立确定性检查，客观 **60/60**。CSV保留产品生成的UTF-8 BOM；输入和题目哈希未变。这是一个探索性episode，**不计正式样本**；manual、总分和纯Harness分均为null。

公开过程为操作人/代理审阅的原生AX标签摘录，仅保留版本、模型、权限、当前评测空间、执行与校验标签、最终结果和产物卡片。账号URL/ID、其他项目和私聊侧栏、规划与推导段、思考内容、系统提示和原始截图均不公开。原始观察保留private哈希，摘录不是完整工具日志；实际Skill、底层模型部署、完整工具请求和执行参数仍不可见，不能据本次正确产物单独给Harness定责。

`metadata.json`记录配置、时间依据与哈希；`visible-events.jsonl`记录实际可见标签及源行号；`verification.json`记录逐项检查；`manifest.json`覆盖公开文件。完整性哈希不单独证明来源真实性。

在仓库根目录复核：

```powershell
python -X utf8 -m harness_eval verify --case T01 --outputs public/pilots/workbuddy-T01-desktop-r1/outputs
```

公开摘录由操作人/代理审阅，未声称经过外部人工审计；按 `received_at` 稳定排序，源行号只对应私有 AX 文件。历史采集/导出源码中如有 “human-reviewed” 或“人工审阅”措辞，仅为当时的说明文本，不能当作外部人工审计证据；历史源码及其哈希保留原字节。metadata 中记录本次说明纠正前的哈希。
