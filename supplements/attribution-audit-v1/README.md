# 五产品归因源审计v1

作者：李明远。日期：2026-10-23。本次是既有公共记录的事后审阅，不是产品实验预注册；新增产品运行0次，不改变旧协议、原件、分数和已发周报。

[assessment.json](assessment.json)保存逐产品判断、置信依据、下一步和停止条件。每款引用本轮S01三个独立任务的实际配置与后台未证实字段，另保留DSH真实Skill调用和观察者接触正文的历史限制。所有来源固定为提交`b8cd4f95e7036e1fd35102fc5e96e430d44e5105`已有字节，不能将旧业务题或之后新版本混进同一轮。

[审计脚本](../../scripts/audit_attribution_boundaries.py)检查公共路径、版本、SHA与JSON指针，逐产品从全部三次S01重新计算条件分母，并与原coverage核对；输出[阅读表](../../reports/attribution-boundaries.md)和[JSON](../../reports/attribution-boundaries.json)。这只核对材料一致性，不自动证明人工解释、原始现场真实性或后台配置。

本版的判定边界：

1. 请求的模型名、界面标签、实际后台部署分别记录。同名标签不升级成后台匹配。
2. `skill_control=partial`表示部分配置受控，`unknown`表示证据不足。`all_skills_disabled_attested=false`表示没有全部禁用的证明，不表示所有Skill都启用。DSH保留Office/诊断Skill且确有调用；Codex的局部发现/扩展开关不能推广到内置和后台状态。
3. 模型、Skill、工具、上下文与环境未同时匹配，独立Harness因果结论不成立，综合因果分保持null。局部产品内对照只支持其记录条件，不自动排除隐藏混杂。
4. 先预定进入边界的条件，再保留全部尝试。只看已形成正确请求的片段会产生选择偏差；条件通过率不作为总体成功率或五产品排名。
5. `eligible=null`保留为资格未证实；不是已知不适用或产品失败。原unknown、上游偏离、缺证和环境有效未证实均保留，不以缺证补零或满分。
6. 字节保真、声明合规、真实请求、状态映射分别解释。工具和执行器未分离时，边界一致不单归Harness；正确模型答题也不单归Harness。
7. 未来实验只有在正式接口能核验控制生效、足以改变具体判断时重新登记。缺乏条件时交付停止记录；不能把自建代理或模拟回合算作五款商业产品的运行。

当前[模型/Skill归因规则](../../docs/attribution.md)继续适用。本轮源审计中的产品条件是历史现场事实；官方文档仅辅助未来预检，不追认为旧运行已经受控。

```powershell
python -X utf8 scripts/audit_attribution_boundaries.py --check
python -X utf8 -m unittest tests.test_attribution_boundaries -v
```
