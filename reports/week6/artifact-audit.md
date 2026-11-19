# 第六周产物审计与开跑决定

2026-11-19，李明远。依据 [Week 5 反馈 #3](https://github.com/llongwang751-arch/tx-harness/issues/3)，本次交付产物审计，关闭两条变体的正式投递。新增产品运行 0 次，正式登记 0 条。第五周的两条 Codex 现场仍为事后登记的 pilot，保留原始 42/60、60/60，继续采用产物一致性口径。

| 反馈项 | 落地证据 | 结论 |
|---|---|---|
| 保留撤回现场 | [事故记录](incidents/doubao-t03-m.json)及锁定的 Git 对象 | 找回九份输出和一份提交提示词，逐字节匹配原发布副本；现存工作区缺输入。会话轨迹、准备时 stderr/退出码、采集和复制日志没有在核查位置恢复 |
| 修订污染归因 | [第五周运行记录的勘误](../week5/run-log-2026-11-13.md) | 输入准备失败，来源未证，运行无效。文件与参考件相同只建立字节相等 |
| 拦截投递 | [准入代码](../../scripts/behavior_preflight.py)及[回归](../../tests/test_behavior_preflight.py) | 准备校验读取实际输入和提示词。缺输入、预建工作区、哈希不符均拒绝，实际可读的评分文件触发拒绝；新变体启动还需事前登记和同一执行权限环境的拒绝记录 |
| 正式开跑条件 | [新登记](../../supplements/behavior-protocol-v2/run-register.json) | 当前没有满足权限证据及独立抽查的适配器。正式登记为空 |

## 豆包事故和证据边界

原工作区仍在本地忽略目录，留存副本与 [11 月 13 日初刊 Git 对象](https://github.com/llongwang751-arch/tx-harness/tree/8a0871fa94014ca103cf5cffb3cd9922e89ea249/public/week5/pilot-doubao-T03-M-r1)的对应文件逐件匹配。记录同时锁定撤回提交和 10 份文件的大小、SHA-256。现存文件和 Git 可以复核字节；第一次准备失败的具体错误和当时是否提交输入，仍依赖操作记录，缺少原始执行回执。产品读取答案、人在复制链误混、现场后续变化均无法靠这些文件区分。没有把同名旧版豆包场次的截图补作本轮证据。

## T03-M 两处失分分别说明什么

| 检查 | 冻结规则与事实 | 判断 |
|---|---|---|
| C06，折合 9 分 | 题面明确只可替换“正式发布：”行的时间并保留其他字节。[实际公告](../../public/week5/pilot-codex-T03-M-r1/outputs/bundle/announcement.md)把标签写为字面量 `$1`，[参考公告](../../cases/T03-M/expected/bundle/announcement.md)有完整标签 | 标签丢失，违反发布公告的保留约束。按字节比对失败的同时存在肉眼可见的内容变化 |
| C01，折合 9 分 | [实际分流文件](../../public/week5/pilot-codex-T03-M-r1/outputs/steps/01_parsed_directive.json)将 P-B 排除，但原因写为 `status=draft_do_not_apply`。[冻结规则和预期](../../cases/T03-M/oracle.json)要求 `draft_do_not_apply`，检查采用 exact JSON。题面只列出 reason 字段，未规定这个原因值的精确字符串 | 冻结评分下失分。此处报告原因字符串与冻结值不同，不能解释为实际应用了草稿指令。未来若制定新版，应在题面写清精确枚举或接受语义等效值 |

高置信范围是产物内容、冻结检查和分值复算。没有凭分数推断模型内部行为、写入先后或跨产品能力。

## 验收命令与重开门槛

```powershell
python -B -X utf8 scripts/behavior_preflight.py --check-closed-register --incident
python -B -X utf8 -m unittest discover -s tests -p test_behavior_preflight.py -v
python -B -X utf8 scripts/week5_pilots.py --check
python -B -X utf8 scripts/verify_behavior_runs.py --check
```

从 `harness_eval prepare` 暂存过的目录仍要经由受控投递入口。变体 CLI 的 `--execute` 先查事前登记；当前登记决定为产物审计，启动器也未接通同权限环境的独立读探针。手工操作第三方 GUI 不受这段代码管理，本轮没有用它绕过投递门。单独使用 `check_access` 只能证明调用它的进程对指定文件的可达性。换盘、目录改名、路径不存在和提示词约定均不给权限隔离证据。提交正式场之前，需新 ID、先提交冻结登记、在同一产品执行主体下实测能读输入哈希却不能打开评分器及答案文件，并取得一位未参与实现者的判卷抽查。公开仓库的网络可达性也应在测试设计中排查。缺任一证据继续交付产物审计。

[判卷抽查操作单](judge-spot-check.md)已备齐，实际独立抽查尚未取得。
