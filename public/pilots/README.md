# 真实预试索引

2026-10-13在独立参与者目录调用已安装产品的原生CLI，保留全部失败与修正尝试。所有目录均为pilot或入口诊断，不能作为正式75个样本，不能据此产生五产品总分或排名。

| 记录 | 结果 | 证据 |
|---|---|---|
| Codex T01 attempt01 | 运行时权限过窄，无交付，环境诊断 | [包](codex-T01-r1-attempt01) |
| Codex T01 attempt02 | 原生交付三文件，8/8通过；collector终结另有枚举错误 | [包](codex-T01-r1-attempt02) |
| WorkBuddy T01 r1 | 关闭设置源，原生CLI返回登录要求 | [包](workbuddy-T01-r1) |
| WorkBuddy T01 r2 | 恢复原生设置源，仍返回登录要求 | [包](workbuddy-T01-r2) |
| DSH T01 r1 | 原生交付三文件，8/8通过；有沙箱错误与替代路径 | [包](dsh-T01-r1/README.md) |

从仓库根目录复核产物：

```powershell
python -X utf8 scripts/verify_public_pilots.py
python -X utf8 -m harness_eval verify --case T01 --outputs public/pilots/codex-T01-r1-attempt02/outputs
python -X utf8 -m harness_eval verify --case T01 --outputs public/pilots/dsh-T01-r1/outputs
```

WorkBuddy没有产品交付，outputs下README是评测员说明，不是产品输出。诊断错误不赋任务零分。Codex原始collector失败与实际native完成分别保留，不静默修正为正式封存包。

各包保留经过审查的原生可见事件，省略隐藏推理、隐藏系统/Skill指令、认证值与个人主目录路径；说明原始日志哈希、过滤规则和记录局限。实际提交文本有预试适配差异，不能声称已严格匹配。manifest只检查公开文件一致性，不证明来源真实性。
