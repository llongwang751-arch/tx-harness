# WorkBuddy窗口重开与续接：一次对照、一处采集缺口

作者：李明远。实测日期：2026-10-22（北京时间）。使用原生Computer Use操作Windows客户端，一次只执行一个任务。本轮真实提交两次：有效通过1次、未知1次，产品失败0次。两次文件验收均通过，但关窗干预缺少必要的中间观察，不能据此判断窗口重开的效果。

## 预先固定了什么

[协议与输入](../supplements/window-reopen-v1/protocol.md)在首次提交前推送，最终登记提交为[`c6d3215`](https://github.com/llongwang751-arch/tx-harness/commit/c6d3215523ec75dbe4bae009d9474c04aab6108f)。[协议JSON](../supplements/window-reopen-v1/protocol.json)绑定了输入、提示词和判卷代码的SHA；之后没有改这些字节。

预检发现两点，均在正式发送前处理。第一，WorkBuddy正常关窗后后台进程仍存在，所以本轮只登记“窗口重开”，不称为应用或进程重启。第二，仓库内空目录会被识别为上层Git仓库和Worktree，因此运行空间及附件副本移到仓库外，产品不接触评测代码。

可见条件为WorkBuddy V5.8.3、办公入口、Deepseek-V4.1-Flash模型标签和“允许完全访问”。对照先做，干预后做；使用同一份128字节UTF-8/LF附件及逐字相同的提示词，各建一个空白工作空间。相同标签不证明后台模型相同，隐藏Skill、自动路由和全局记忆也未固定。两次初始页面的侧栏布局不同，保留为观察条件差异，不将本对说成完全隔离所有变量。

第一阶段复制附件为stage-a.txt；取得原件并记录检查点后，120秒发送同一句“按初始要求继续第二阶段。”，容差±15秒。第二阶段复制为stage-b.txt，并交付四字段receipt.json。每个完整任务算一次运行，两阶段、截图和评分项不另算。

## 实际结果

时间均为北京时间。封存时间表示评测侧已实际取得原件，不是产品纯生成耗时，也不用于速度排名。

| 项目 | W01保持窗口 | W02关窗/重开命令 |
|---|---|---|
| 初始提交 | 00:30:09 | 00:37:20 |
| 检查点 | 00:31:51 | 00:39:11 |
| 续接延迟 | 122.745秒 | 120.010秒 |
| 原件封存 | 00:34:59，提交后290.814秒 | 00:41:54，提交后274.362秒 |
| Stage A及后续重取 | 与128字节输入一致 | 与128字节输入一致 |
| Stage B及receipt | 两份原件取得，冻结判卷通过 | 两份原件取得，冻结判卷通过 |
| 运行有效性 | 有效，通过 | 干预条件未知，结果不列有效通过 |
| 现场与判定 | [逐项审阅](../public/supplements/window-reopen-v1/W01-control/review.json)、[最终原生截图](../public/supplements/window-reopen-v1/W01-control/scenes/final.png) | [逐项审阅](../public/supplements/window-reopen-v1/W02-window-reopen/review.json)、[最终原生截图](../public/supplements/window-reopen-v1/W02-window-reopen/scenes/final.png) |

两份txt的SHA均为`d7e5f5aea847b82e1351dbc481259bca0c87db74b1960e634b15a809ad88f0be`。receipt中的stage/source/bytes/sha256均正确，没有额外字段或重复键，bytes为整数。[W01判卷](../public/supplements/window-reopen-v1/W01-control/judgment.json)、[W02判卷](../public/supplements/window-reopen-v1/W02-window-reopen/judgment.json)直接由公开原件重算，不采信产品自己的“已校验”作为判卷结果。

## 哪些判断成立

**已取得文件的字节符合规则，高置信。** 每次取回均保存原始副本、来源界面、实际时间、大小和SHA；复制前后源SHA相同。两臂各有5条收集记录，覆盖Stage A初收、后续重取，以及最终三份文件。公开[封存清单W01](../public/supplements/window-reopen-v1/W01-control/seal.json)和[W02](../public/supplements/window-reopen-v1/W02-window-reopen/seal.json)与收集日志、每个副本、最终交付字节对应。来源及时间仍由同一Operator采集，因此现场真实性与时间为中置信，哈希本身不能证明桌面操作真实。

**重开命令后的原消息及文件仍可访问，中置信。** W02恢复界面的任务标题、原始完整消息、00:37创建时间、附件标签和仅完成Stage A的状态与干预前对应；[恢复现场摘录](../public/supplements/window-reopen-v1/W02-window-reopen/scenes/restored-message.json)和[原生截图](../public/supplements/window-reopen-v1/W02-window-reopen/scenes/restored.png)可核对。这个判断限于观察时可访问的状态，不证明模型实际收到的完整上下文，也不能补足“窗口确实关过”的缺口。

**附件存储字节保留未知。** 只观察到probe.txt卡片、主机源文件路径和正确的交付文件，没有从产品存储中独立取回原始附件。主机文件一直存在、模型再次读到它、Stage A正确，都不能证明Harness自身存储了同一附件。该项不记零分或满分。

## 为什么这对不能验证关窗效果

现象：[W02干预记录](../public/supplements/window-reopen-v1/W02-window-reopen/intervention.json)显示已发正常关闭命令，但紧随其后的窗口清单仍列出目标窗口；随后发出了启动命令。后续界面恢复，文件也正确。

原因线索：观察清单与关闭动作相隔很短，可能碰到异步关闭过程；但也不能排除窗口未按预期关闭。当前证据不能在这两种解释中作选择。

验证结论：可以确定采集流程在启动前没有留下“窗口已消失”的记录；不能确定关窗实际成立，也不能证明产品保存状态失败。之后结束测试时观察到了空窗口清单，这发生在第二阶段封存以后，不能用来补证之前的干预。未知责任先记在实验执行与采集链，不算产品失败。

依登记的停止条件，本对结束即停止，不重跑来换一组更完整的结果。U06保留此次缺口并关闭追补：这段历史不能事后复原；以后若再做，需另登记协议，要求在启动前观察到窗口消失。U07单列附件字节未知；若没有原生取回入口，就停止追查这一指标。模型、Skill、路径、固定执行顺序和全局记忆仍未排除，故本报告不提供Harness独立因果结论或五产品排名。

## 如何复核

[现场包索引](../public/supplements/window-reopen-v1/README.md)包含原件、逐次收集副本、提交时间、配置、经审阅的AX摘录及未裁改原生截图。完整AX含账户和其他历史，留在私有目录；公开摘录保留来源行号和原始文件SHA。它们仍是单人采集材料，尚无外部独立复核。

```powershell
python scripts/verify_window_reopen.py
python scripts/window_reopen.py --probe supplements/window-reopen-v1/fixtures/p1/probe.txt --outputs public/supplements/window-reopen-v1/W01-control/outputs
python scripts/window_reopen.py --probe supplements/window-reopen-v1/fixtures/p1/probe.txt --outputs public/supplements/window-reopen-v1/W02-window-reopen/outputs
python -m unittest tests.test_window_reopen tests.test_window_reopen_evidence -v
```

冻结的文件判卷有5项回归检查；新增证据复核有7项检查，包含空清单、缺少原件、重复记录、篡改字节及填报延迟与真实时间不符的反例。这12项是评测代码检查，不增加产品运行次数。旧协议、旧分、封存包和已发送周报未改。
