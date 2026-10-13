# 真实预试索引

2026-10-13至14（Asia/Shanghai）在独立参与者目录通过产品原生CLI、SDK和正常桌面入口执行或恢复观察，保留全部失败与修正尝试。当前24个公开包、19次后验评分，已完成18/25个产品×任务组合。所有目录均为pilot、产品侧失败或入口诊断，不能追认为正式75个样本。后验评分另见[探索性审阅](../../reports/exploratory-score-review.md)，完整覆盖及纯Harness因果排名的限制见[分析口径](../../docs/exploratory-analysis-plan.md)。

| 记录 | 结果 | 证据 |
|---|---|---|
| Codex T01 attempt01 | 运行时权限过窄，无交付，环境诊断 | [包](codex-T01-r1-attempt01) |
| Codex T01 attempt02 | 原生交付三文件，8/8通过；collector终结另有枚举错误 | [包](codex-T01-r1-attempt02) |
| WorkBuddy T01 r1 | 关闭设置源，原生CLI返回登录要求 | [包](workbuddy-T01-r1) |
| WorkBuddy T01 r2 | 恢复原生设置源，仍返回登录要求 | [包](workbuddy-T01-r2) |
| DSH T01 r1 | 原生交付三文件，8/8通过；有沙箱错误与替代路径 | [包](dsh-T01-r1/README.md) |
| Codex T04 attempt01 | 采集器误把未来计划判为主动请求；7/7产物不能使恢复样本有效 | [包](codex-T04-r1-attempt01/README.md) |
| Codex T04 attempt02 | 明确请求、同一thread续接；三文件7/7；适配器kill/resume | [包](codex-T04-r1-attempt02/README.md) |
| DSH T04 r1 | 同一SDK进程/session两轮；三文件7/7；18.052秒观察员延迟 | [包](dsh-T04-r1/README.md) |
| Codex T02 attempt01 | 四原生文件，7/7；一次覆盖预试，模型未知 | [包](codex-T02-r1-attempt01/README.md) |
| Codex T03 attempt01 | 五原生文件，6/6，包括保护文件字节一致；模型未知 | [包](codex-T03-r1-attempt01/README.md) |
| Codex T05 attempt01 | 三原生文件，8/8；一次覆盖预试，模型未知 | [包](codex-T05-r1-attempt01/README.md) |
| WorkBuddy T01 desktop r1 | 正常桌面三原件，8/8；E2界面证据；59.495秒观察区间上界 | [包](workbuddy-T01-desktop-r1/README.md) |
| WorkBuddy T02 desktop r1 | 四原件，7/7；64.675秒观察区间上界 | [包](workbuddy-T02-desktop-r1/README.md) |
| WorkBuddy T03 desktop r1 | 五规定原件，6/6；保护字节一致；64.247秒上界 | [包](workbuddy-T03-desktop-r1/README.md) |
| WorkBuddy T04 desktop r1 | 真实缺失请求、同一可见任务补发；三原件7/7；116.359秒上界，内部session未知 | [包](workbuddy-T04-desktop-r1/README.md) |
| WorkBuddy T05 desktop r1 | 三原件，8/8；净额18599；40.659秒上界 | [包](workbuddy-T05-desktop-r1/README.md) |
| DSH SDK T01 r1 | 三原件，8/8；与headless不同profile | [包](dsh-sdk-T01-r1/README.md) |
| DSH SDK T02 r1 | 四原件，7/7；同账号四任务并发之一 | [包](dsh-sdk-T02-r1/README.md) |
| DSH SDK T03 r1 | 五规定文件与九个native探针全保留，6/6 | [包](dsh-sdk-T03-r1/README.md) |
| DSH SDK T05 r1 | 三原件，6/8，产物30/60；错误与金额差异保留 | [包](dsh-sdk-T05-r1/README.md) |
| 元宝专家模式 T01 desktop r1 | 三原件，7/8，产物42/60；两笔排除订单净额错误；文件取回超预算限制明确保留 | [包](yuanbao-T01-desktop-r1/README.md) |
| 元宝专家模式 T02 desktop r1 | 四原件4/7、27/60；Q006少计60000分及冲突ID排序错误；首次完整回复四卡709.135秒，原错完成记录更正、末件取回晚于预算 | [包](yuanbao-T02-desktop-r1/README.md) |
| 豆包工作任务·本地电脑 T01 desktop r1 | 产品回复沙盒准备480023，未生成文件；0/8，产物0/60；产品侧failed，不作采集无效剔除 | [包](doubao-T01-desktop-r1/README.md) |
| 豆包工作任务·云电脑 T01 desktop r2 | 三原件8/8、60/60；采集中断后1540.504秒首次观察完成，预算有效性为false，非精确服务耗时；本地失败仍另列 | [包](doubao-T01-desktop-r2/README.md) |

从仓库根目录复核产物：

```powershell
python -X utf8 scripts/verify_public_pilots.py
python -X utf8 -m harness_eval verify --case T01 --outputs public/pilots/codex-T01-r1-attempt02/outputs
python -X utf8 -m harness_eval verify --case T01 --outputs public/pilots/dsh-T01-r1/outputs
python -X utf8 -m harness_eval verify --case T04 --outputs public/pilots/codex-T04-r1-attempt02/outputs
python -X utf8 -m harness_eval verify --case T04 --outputs public/pilots/dsh-T04-r1/outputs
```

WorkBuddy两份CLI诊断包没有产品交付，outputs下README是评测员说明；五desktop包另有实际原件。诊断错误不赋任务零分。Codex原始collector失败与实际native完成分别保留，不静默修正为正式封存包。DSH SDK四项并发耗时不能视作单任务速度，T05失败不剔除，T03额外探针不伪装为评测者产物。所有T04包的rates是补发资料，不能复现时预先给产品。

各包保留经过审查的原生可见事件，省略隐藏推理、隐藏系统/Skill指令、认证值与个人主目录路径；说明原始日志哈希、过滤规则和记录局限。实际提交文本有预试适配差异，不能声称已严格匹配。manifest只检查公开文件一致性，不证明来源真实性。
