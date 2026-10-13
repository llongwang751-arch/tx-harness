# 现场采集操作单

## 冻结之前

1. 阅读产品登记，确认公告里的“豆包办公”对应哪个入口；实际记录元宝专家模式入口、DSH模式、Codex桌面版本。不要用API版成绩代替桌面版。
2. 对五产品各做不进入主分母的预试（`--track pilot`）。检查上传、文件导出、模型锁定与记录方式。按发现修订任务，而不是按优劣调整权重。
3. 确认 `config/protocol.json` 后，将status改成preregistered并冻结Git commit。任务、提示词、答案和分值一并冻结。
4. 运行audit、单元测试和plan。75个实验位按计划顺序执行；模型若在中途更新，不混入同一批次，另开批次说明。

## 每次运行

1. `prepare` 创建独立实验目录。把 `workspace` 复制到产品可访问的独立目录或只上传其中的inputs。产品不得访问评测仓库、oracle、评分脚本、其它产品记录或releases。
2. 开全新会话，清空跨任务记忆/自装Skill（无法关闭则记下）；选定并保持模型。开始前完成基础文件授权。填meta.json：操作员、surface、mode、产品版本、模型、Skill条件；记录account_tier、region、memory_condition、permissions、environment与不可见项。无法得知的版本/模型填 `not_disclosed`，明确model_visibility和现场依据；不用猜测。各产品内部的登记条件保持一致；声明相同并不能证明隐藏模型或内置Skill相同。
3. 仅发送prompt.md的原文；通过上传或目录挂载提供inputs，不额外解释预期答案。若路径需要适配，使用同一预注册替换规则并记录它。开始屏幕录像/导出用户可见会话，并从首次提交任务开始20分钟计时。
4. 将开始证据置于evidence/，用 `event --kind start` 登记原始发生时间。操作员实时记录工具调用、错误、确认、恢复、用户帮助与产物；原生工具日志不可见时直接写“不可见”，不补造调用。
5. T04按release_protocol补发；2分钟内主动请求即可补发，否则2分钟预定补发并记为被动。补发本身是协议事件，不计人工干预。补发后固定回复并续用原会话。
6. 任何额外提示/修复记为intervention，最多2次。统一20分钟包括用户等待；产品仍运行时到点停止，冻结此时产物。预算内无交付则保留空outputs，不帮助它重写。
7. 下载/复制产品原生生成文件到workspace/outputs。保留原名；归档可按原名解压。下载/复制期间不更改内容、换算数值或手工编写文件。登记artifact、finish事件及证据。
8. finalize登记终态。在manual.json逐维赋分，引用已有事件。对截屏、导出文本和输出文件作人工公开审查；删除用户名、聊天中其他人信息、密钥、会话链接中的访问令牌。在封存前完成脱敏，再填redaction_reviewed=true。
9. seal之后运行score；export复制到public/runs。旧封存不静默改写；补证/更正保留旧包和更正说明，并从主实验汇总中明确替代关系。

## 最小证据包

| 文件 | 内容 |
|---|---|
| meta.json | 运行条件、时间、终态、人工干预计数、录制局限、初始输入哈希 |
| evaluation_snapshot.json | 冻结的工具代码、协议、用例和评分规则哈希 |
| events.jsonl | 有时间与事件ID的可见过程，引用evidence文件和SHA-256 |
| evidence/ | 公开前审查过的录像/截图/聊天导出；不同事件可引用同一连续录像的不同时间段 |
| workspace/prompt.md、inputs/ | 产品收到的提示词和实际输入；T04补发单独登记 |
| workspace/outputs/ | 产品在预算截止前交付的原始文件 |
| manual.json | 四个人工维度的等级、理由、置信依据、替代解释、复核引用 |
| manifest.json | 封存时所有文件的SHA-256；它证明封存后一致性，不证明现场真实性 |

引用连续录像时，事件summary写清 `00:01:23–00:01:40`；引用长会话文本写清行号/消息号。只取截屏时不能推断未观察到的背景步骤。保留产品界面自述“成功”和实际失败两者，便于区分主张与事实。没有权限读取的隐藏推理、服务端日志不作为必需证据。

## CLI示例（命令本身不生成产品成绩）

```powershell
python -m harness_eval audit
python -m unittest discover -s tests -v
python -m harness_eval plan
python -m harness_eval prepare --product codex --case T01 --replicate 1 --track pilot
```

以下以已经复制到 `runs/pilot-codex-T01-r1/evidence/` 的真实截屏/录制为例。先填写meta，再登记事件；不存在的证据文件会使命令报错。

```powershell
python -m harness_eval event --run runs/pilot-codex-T01-r1 --kind start --summary "新会话提交统一任务；start.png包含模式和输入" --evidence evidence/start.png
python -m harness_eval event --run runs/pilot-codex-T01-r1 --kind tool_result --summary "录制00:00:30到00:00:50：读取输入并返回统计" --evidence evidence/session.mp4
python -m harness_eval event --run runs/pilot-codex-T01-r1 --kind finish --summary "预算内结束，已交付文件，见结束画面" --evidence evidence/finish.png
python -m harness_eval finalize --run runs/pilot-codex-T01-r1 --status completed --note "按实际现场填写终态原因"
```

离线整理事件时使用 `--at 2026-10-13T10:00:00+08:00` 指定真实发生时间，不能把整理时间冒充执行时间。按事件发生順序录入。填写manual、完成脱敏后：

```powershell
python -m harness_eval seal --run runs/pilot-codex-T01-r1
python -m harness_eval score --run runs/pilot-codex-T01-r1
python -m harness_eval export --run runs/pilot-codex-T01-r1 --out public/runs/pilot-codex-T01-r1
python -m harness_eval report --runs-dir public/runs --out reports/summary.md
```

汇总只收product_default轨道，pilot/attribution保留在公开仓库，但不混入主统计。补充归因实验暂由人工按attribution.md记录；工具不提供虚构的五产品自动执行适配器。

T04补发命令必须记录active或passive。active引用已有、带请求现场证据的事件ID（示例E002）；passive在开始后120秒或更晚执行。`--at`只用于回填真实原始时间，不用于制造符合预算的记录。

```powershell
python -m harness_eval release --run runs/pilot-codex-T04-r1 --mode active --request-event E002 --note "120秒内主动请求；见E002；补发后另记界面上传现场"
python -m harness_eval release --run runs/pilot-codex-T04-r1 --mode passive --note "120秒仍未请求，按协议预定补发；另记界面现场"
```

以上二选一；同次任务只能补发一次。CLI验证文件、次数与时间窗口，语义上是否真的请求仍由评测员和复核者按现场判断。
