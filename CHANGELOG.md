# 变更记录

按北京时间记录已经完成并留在仓库中的改动。历史条目根据Git提交补记，后续计划写在[个人周报](reports/weekly/README.md)中。

## 2026-10-22

- 通过官方原生Computer Use恢复WorkBuddy桌面实测，一次只执行一个任务；登记[窗口重开v1协议](supplements/window-reopen-v1/protocol.md)后真实提交两次。预检确认关窗不等于进程退出，并在首次发送前将产品输入及工作空间移出评测仓库。
- 公开[两份新现场包](public/supplements/window-reopen-v1/README.md)、原生截图、任务AX摘录、逐次原件和封存清单。两次文件验收通过；W01有效通过，W02因启动前未留下窗口消失观察而记未知，保留采集缺口，不重跑替换，不据此证明关窗效果或产品失败。
- 新增[分析报告](reports/window-reopen-v1.md)，分开消息/卡片可访问、已取得字节、附件存储未知和干预未知。实际收集均在1200秒预算内封存；续接延迟为122.745秒与120.010秒，不用封存耗时作速度排名。
- 增加冻结文件判卷与证据复核的12项回归，覆盖缺文件、重复键、换行变化、空封存清单、漏收集、字节篡改及虚填延迟。复核固定登记提交，并交叉检查每份原件、收集日志、封存清单及真实时间。
- 更新[运行登记](supplements/week2/executions.json)和[文字周报草稿](reports/weekly/2026-10-24-draft.md)：新增2、有效1、失败0、未知1、环境无效0。新增两项未知及停止条件，下周仍最多三项主要目标。旧协议、评分、封存包和已发周报不改。

## 2026-10-21

- 准备[检查点后重开原任务的实测草案](docs/reopen-experiment-draft.md)：先测WorkBuddy，最多两对四任务，区分不重开对照、正常退出干预、状态保留与联合交付，列出截止收集材料和停止条件。正式入口及具体操作尚需预检与冻结，未执行，不计新增产品运行。
- 按本周新验收要求完成[第二周阶段报告](reports/week2/stage-report.md)。本周新增独立产品运行0；合成答案、守卫开关和旧产物复算分别统计，不把评分条目当作运行。
- 新增版本化有效性验收器，修正CSV损坏引用被恢复、T03修改清单多出字段、JSON转义攻击标记漏检三类缺口；原harness_eval、用例、权重、已封存包和历史分保持不变。
- 公开22组固定合成样例（10组合规、12组不合规）：旧版误接受4组，新版这批误接受0、误拒绝0；完成20次守卫开关核查，结果与预期一致。旧25个选定现场只读重验，新增拒绝0。材料见[判卷审计](reports/grader-audit-v3.md)，不将针对性回归当成产品可靠性结论。
- 为[六条重点结论](reports/week2/claims.json)绑定规则版本、输入、配置、现场、原件、理由及置信范围，分别写现象、原因线索、验证结论和未排除因素；[五项未知](supplements/week2/unknowns.json)设定下一步及停止条件。
- 准备[两条结论外部复核包](reports/week2/external-review-packet.md)，当前尚未收到外部复算意见。新增[10月24日文字周报草稿](reports/weekly/2026-10-24-draft.md)，数据截至21日，尚未发送；[下周计划](supplements/week2/next-week-plan.json)限制三项并注明规模与完成条件。
- 首次Linux CI发现合成元数据的跨平台键序差异：T04的README/rates在Windows和Linux排序不同，导致G4/N4元数据及manifest字节漂移。用平台排序模拟复现后，为生成器规定稳定顺序并增加回归；保留已公开样例字节和[首次失败记录](https://github.com/llongwang751-arch/tx-harness/actions/runs/39556898818)，未改业务判定或产品原件。

## 2026-10-20

- 完成一次仓库实质复核：原补测导出遗漏6份已脱敏核查附件，影响四项主观察12处、含额外交付/声明共17处引用。按原metadata/review已登记SHA补充公开，新增[证据定位审计](public/supplements/contracts-v2/evidence-locators.md)及CI检查；原包、观察判定和旧分未改。文字型引用保留人工复核状态。
- 修正后续导出的附件门槛：只允许显式登记的已审阅附件，拒绝缺失公开定位或哈希不符；为断链、篡改、路径逃逸和未审阅附件新增离线回归检查。未重新运行产品。
- 补充E2交付指标的已取得/未取得/比对不符分母，S02拒绝臂缺文件不算字节失败；条件指标分母另列原资格和明确环境无效的排除数，当前通过/失败数不变。
- 新增[已执行方案](docs/evaluation-plan.md)和[报告索引](reports/README.md)，修正75轮未实施草案入口，并披露旧评分JSON中滞后的覆盖状态字段。报告补入研究方法、评分公式及证据修订；明确旧评分器未绑定截止快照、严格截止分保持未知，以及跨产品模型/Skill归因仍未完成。
- 根据本人提供的姓名李明远，补全仓库首页、书面报告作者及周报主题、自我介绍和落款，周报模板同步填写姓名。
- [周报公开归档](reports/weekly/2026-10-17.md)注明署名补全日期，保留[发送前占位稿](https://github.com/llongwang751-arch/tx-harness/blob/7f4ab6096d647cd3e97c5f5fbe678bd8991b3bd8/reports/weekly-2026-10-17-draft.md)、[首次归档版本](https://github.com/llongwang751-arch/tx-harness/blob/d54d0d9f803b93e4fe1544c913f0df811067b172/reports/weekly/2026-10-17.md)及新旧内容校验值。邮件留存内容仅替换姓名占位，业务正文和评测结果未改。

## 2026-10-19

- 新增本变更记录，补齐项目建立、五产品任务复现、方法修订和周报整理的历史入口。
- 新增[周报索引](reports/weekly/README.md)及[2026-10-17周报归档](reports/weekly/2026-10-17.md)。本人于2026-10-19确认邮件已发送，正文与仓库原稿一致；归档保留原稿版本和正文校验值，实际发送时间未单独记录。
- 更新首页、提交说明和报告中的周报状态，保留[发送前占位原稿](https://github.com/llongwang751-arch/tx-harness/blob/7f4ab6096d647cd3e97c5f5fbe678bd8991b3bd8/reports/weekly-2026-10-17-draft.md)。修订[周报模板](reports/weekly-template.md)，去掉未实施的75次实验固定分母。
- 本次只整理文档和归档入口，没有新增产品测试或修改既有原件、评分。

## 2026-10-17

- 将周报改为个人复盘的语气，说明方法调整、题目区分度不足及下周安排。对应提交：[d2a9d55](https://github.com/llongwang751-arch/tx-harness/commit/d2a9d55)。
- 完善邮件主题、自我介绍、称呼和落款，形成[发送前留存稿](https://github.com/llongwang751-arch/tx-harness/blob/7f4ab6096d647cd3e97c5f5fbe678bd8991b3bd8/reports/weekly-2026-10-17-draft.md)。对应提交：[7f4ab60](https://github.com/llongwang751-arch/tx-harness/commit/7f4ab60)。

## 2026-10-16

- 在首次补测前登记21个实验位及固定输入、提示词、执行和判定规则。登记提交：[1473d36](https://github.com/llongwang751-arch/tx-harness/commit/1473d3602c67ee2debcbb96e951df580f9c3d422)。
- 完成五产品各三次固定文件任务，以及Codex三组允许/拒绝写权限配对，合计21轮。实际过程、原件和指标分母见[补测索引](public/supplements/contracts-v2/README.md)。完成提交：[3d1c7b9](https://github.com/llongwang751-arch/tx-harness/commit/3d1c7b931b08f62cf4333797b98587c91d17b0dc)。
- 发布[报告v2](reports/report.md)和[逐字段复核](reports/evaluation-v2.md)，分开业务结果、可见执行边界和归因未知，保留旧协议、原件及分数。核对三组权限配对的实际启动条件，不将它们外推为五产品纯Harness排名。
- 修正后续采集的隐私过滤与引用方式，记录版本、源哈希和限制。DSH第二轮采集问题及修正经过见[方法修订](docs/revision-v2.md)，没有因此重跑或覆盖已封存现场。

## 2026-10-14

- 完成原五产品各五题的25个选定组合，保留31个公开包和26次评分，失败、入口诊断、重试及预算局限另列。对应提交：[2cca52a](https://github.com/llongwang751-arch/tx-harness/commit/2cca52afbc6744c6b27c7127ced70162a03f5a32)。
- 原报告现保留为[报告v1](reports/report-v1-2026-10-14.md)，原始评分与证据可继续复核。

## 2026-10-13

- 建立Python标准库评测工具、五套用例及方案、采集、评分和归因文档，开始保存真实接入记录。初始提交：[0b69a2a](https://github.com/llongwang751-arch/tx-harness/commit/0b69a2a)。
