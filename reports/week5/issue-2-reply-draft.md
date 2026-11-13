# Issue #2 回复草稿（2026-11-13）

> 用途：由本人粘贴到 Issue #2 作为评论，不代发。链接为 `codex/evaluation` 分支相对路径，粘贴后可保留原样。

---

感谢批改。四条要求逐条回应如下。本轮的关键变化是：**不再只交计划**——决策门给的是带依据的不运行决定，对抗审计给的是"伪造能满分"的实测结果，快照门已经进 CI。

**问题1（什么证据会让我们决定不运行；若协议可执行，延期阻塞是什么）**

不运行的理由不是"还没准备好"，是三条可核对的事实，写在[决策门记录](../blob/codex/evaluation/reports/week5/decision-gate-2026-11-14.md)：

1. **产品入口**：五款都是外部商业应用，本机没有可用会话、账号或 GUI 自动化通道，10 个实验位产生不了真实运行；用合成产物冒充会违反台账规则。
2. **可核验事件流**：五款均无工具调用/请求事件，DSH 与 Codex 的受控事件不覆盖这两条变体。没有它，"步骤是否真的发生"不可证。
3. **模型与 Skill**：五款后端模型均未证实，GUI 三款 Skill 未知，跑完也只能写"该配置下的端到端表现"。

**预期信息增益**：10 次运行能得到的只是产物一致性读数；得不到过程真实性、Harness 归因或排名。下面问题2的实测说明，最关键的未知（步骤是否发生）不会被这 10 次运行回答。**重开条件**写死为两条同时满足：拿到可复现入口 + 可核验事件流；重开另写决策记录，不改旧文件。

**问题2（能否构造"伪造中间步骤但最终文件自洽"的答案骗过判卷器）**

**能，而且是满分**。为两个变体各造三条臂（[对抗审计](../blob/codex/evaluation/reports/week5/adversarial-artifacts.md)，`python scripts/audit_adversarial_artifacts.py --check` 可复核）：

| 臂 | T03-M | T05-M |
|---|---:|---:|
| 步骤整目录不交（最终文件正确） | 42/60 | 45/60 |
| **先把最终产物做对，再反推补写步骤文件** | **60/60** | **60/60** |
| 一个业务值改错但三处自洽 | 45/60 | 27/60 |

结论：步骤文件是"申报"不是"证据"——内容完全由输入+最终产物决定，判卷器不看写入顺序、时间戳或调用轨迹；只有不交才掉分，自洽的错值仍被精确扣分。据此已按要求改名并加维度：60 分在[正式比较表](../blob/codex/evaluation/reports/week3/formal-table.md)的"判卷覆盖范围"里改称**产物一致性分**，另设**原生调用证据**（五款 `not_obtained`，不并入分数、不因缺失扣分），口径说明见 [grading-scope](../blob/codex/evaluation/docs/grading-scope.md)。

**问题3（干净克隆能复算，题目/标签正确性如何取得独立意见）**

如实说：现在没有独立意见。新增的[自证边界](../blob/codex/evaluation/reports/week5/self-verification-boundary.md)列了自证能回答的四件事（确定性、自包含、内部一致、算术）和回答不了的五件事，其中第 2 条（步骤是否发生）与第 5 条（后端模型是否与标签一致）本轮已拿到实证：前者由对抗审计证明可伪造，后者五款均无 attestation。第 3、4 条（判卷器对近似正确的判断、题面与标签）仍只能靠外部意见。

**P0（决策门）**：[decision-gate-2026-11-14.md](../blob/codex/evaluation/reports/week5/decision-gate-2026-11-14.md) + [decision-gate.json](../blob/codex/evaluation/reports/week5/decision-gate.json)：决定、阻塞、预期信息增益、停止条件（协议四条均未触发）、重开条件。**当晚增补**：拿到可用入口后没有停在决定上，实际跑出三条——[Codex T05-M 60/60、Codex T03-M 42/60、豆包工作任务模式 T03-M 60/60](../blob/codex/evaluation/reports/week5/run-log-2026-11-13.md)，证据包在 [public/week5](../blob/codex/evaluation/public/week5/manifest.json) 逐文件带哈希。**一并更正**：先前"豆包不落盘"是跑在「对话」页的结论，被测入口应是「工作」页；切对入口后豆包九个文件全交付、十项全过。这属于入口错配，不是产品能力结论，已撤回。元宝记环境无效（Linux 沙箱读不到本机目录），WorkBuddy 记未运行（合成文本输入被拒）。10 个位实际完成 3 个，`slots` 不虚报。

**P1（对抗性产物）**：见问题2；六条臂全部由脚本从冻结输入确定性构造，不是产品运行，不进台账、不改五题分数。

**P1（结论、快照与哈希一起版本化）**：[index.json](../blob/codex/evaluation/ledger/conclusions/index.json) 把四条结论的文本哈希、证据清单与 Git blob 绑在一起，`scripts/verify_conclusion_snapshots.py --check` 已进 CI。实测流程：改了 CL-01 证据哈希但没记录 → `--check` 直接报"结论文本已变，但没有新增差异记录"；补 `--record --reason` 后才通过。旧快照按 blob 可取回，不再依赖人工在 pin_note 里追补。

**P1（自证边界）**：见问题3的文档。

仍缺的一件：一位未参与实现的人复跑一条判据并签署记录。操作单与记录表保持公开（[independent-review](../blob/codex/evaluation/ledger/independent-review/2026-11/README.md)），收到就原样归档，不冒领。
