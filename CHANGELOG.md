# 变更记录

按北京时间记录已经完成并留在仓库中的改动。历史条目根据Git提交补记，后续计划写在[个人周报](reports/weekly/README.md)中。

## 2026-10-25

- 整理第2周文字周报，统计窗口为10月18日至24日，落款25日；仍为未发送草稿，由本人写入邮件。25日没有新增产品实测，不生成PDF、不代发邮件。
- 补公开24日WorkBuddy三次原生固定响应校准的[现场与审计](reports/controlled-workbuddy.md)：独立任务3、正式对照0、通过0、未知3、产品失败0；WBC02原生终态未知，HTTP服务期限不当产品终态。旧两包未覆盖，第三包按字段白名单导出。
- [第二周台账](supplements/week2/executions.json)由11次增至14次，有效9、失败0、未知5；真实模型4次，固定响应10次（含校准6次、正式4次）。两次接受前配置拒绝另列；三款GUI接口预检计零任务。公开已接受任务包由52增至66。
- 同步[Markdown周报](reports/weekly/2026-10-24-draft.md)、阶段报告、主报告索引与未知登记。已完成的GUI预检移出下周待办；三项目标列交付、规模、验收及停止条件。
- 追加原生接受准入与计数回归，将WorkBuddy公开包审计和GUI预检复核加入CI。本机全套226项离线回归无失败、1项跳过，15项交付检查及公开字段/链接检查通过。旧原件、冻结协议、历史分数和已发送10月17日周报保持不变。

## 2026-10-24

- 实现[本地固定响应服务](scripts/controlled_model_fixture.py)、[共享MCP](scripts/controlled_probe_mcp.py)与[官方CLI/SDK运行入口](scripts/run_controlled_adapter.py)，真实Codex 0.159.2和DSH 0.2.1-rc.2接入同一冻结动作；不使用账户密钥或神经模型。DSH版本另记，未混入旧S01。
- 先校准入口，再于首次正式提交前推送[`1a03e16`](https://github.com/llongwang751-arch/tx-harness/commit/1a03e16)冻结四臂。[实际现场](public/supplements/controlled-adapter-v1/README.md)显示四次正式任务均完成参数、执行效果、结果回传及正常终止：两份成功原件125字节且摘要相同，两次错误保持固定错误内容并无产物。
- 保留校准五次启动及四个登记版本：两次接受前配置拒绝不算独立任务；三次接受任务中两通过、一审批适配器未知。没有覆盖失败或把未知记产品低分。所有本轮记录的测试产品/MCP进程均已退出，一次只运行一个实际产品。
- 公开[专项报告](reports/controlled-adapter-v1.md)、[逐项复算](reports/controlled-adapter-v1.json)和九份证据包。模型固定程序不解释Skill；Codex仍检测到相关标题，不宣称全部Skill已删除。wire、schema包装和系统上下文保留差异，可信宿主MCP不测沙箱。GUI三产品仍在原真实任务轨道，未发布五产品纯Harness排名。
- 新增34项离线测试，覆盖真实HTTP两种SSE、MCP字节与错误路径、重封manifest后的参数/回包/Unicode/隐藏文件/调用ID/接受任务造假及历史登记绑定。本机全套186项检查无失败，1项因Windows符号链接权限跳过；最终判卷13项复查通过。旧原件、旧分、已发周报和旧封存材料保护核查通过。
- 更新[周报草稿](reports/weekly/2026-10-24-draft.md)、阶段报告、未知及最多三项下周目标。本周共11次已接受任务，有效9、失败0、未知2；其中真实模型4次、固定响应7次分列，另两次配置拒绝单列。环境变量值不公开，保留原始值摘要；周报由本人发送，尚未发送。

## 2026-10-23

- 完成[五产品归因边界表](reports/attribution-boundaries.md)与[源审计JSON](reports/attribution-boundaries.json)：固定已有提交，逐款核对S01三轮实际模型/Skill条件、原件与内部边界。不同批次版本分列，模型请求/标签不升级为后台身份。
- 明确DSH关闭用户/项目Skill发现但保留Office/诊断Skill，第二、三轮有真实调用；保留第二轮观察者曾经投影接触正文的历史限制。Codex局部发现/扩展开关、GUI未知状态均不冒充全部Skill已关闭。
- 新增[离线源审计](scripts/audit_attribution_boundaries.py)与13项回归：保留全部尝试、资格未证实、上游偏离与缺证，核对条件分母；阻止材料计入新运行、遗漏三轮配置、错误来源及归因范围漂移。代码检查不等于因果证明或外部人工复核。
- 全套152项离线回归通过；旧31包、21轮补测、两批窗口现场、归因源审计和旧分保护检查通过，195处本地链接无断链。原件和已发周报字节保持不变。
- 本次复核旧15轮，新增产品运行0次；本周仍为新增4、有效通过3、失败0、未知1。归因边界表提前完成，从下周待办移至已完成记录，文字周报和阶段报告同步更新。当前材料不足以启动有意义的共同模型/完整Skill消融，本批停止更强推论；仅在正式生效证据改变具体判断时另登记。

## 2026-10-22

- 同日后续：先完成无模型提交的原生另存与关窗预检，再冻结推送[v2协议](supplements/window-reopen-v2/protocol.md)，真实提交R01重开、R02保持窗口各一次。主观察在固定续接前完成，前后四份直接取回一致，最终三份文件验收通过；R01启动前连续两次窗口清单为空。见[v2报告](reports/window-reopen-v2.md)和[新现场](public/supplements/window-reopen-v2/README.md)。
- 每臂七次实际文件收集与封存清单对应，续接延迟180.006秒和180.001秒，分别690.030秒、380.422秒内封存。新增公开复核检查版本、原件、界面取回来源、关窗顺序和实际时间；仅本地UI交付结论，不证明独立云存储或后台模型/Skill匹配。
- 本周当前合计新增4次，有效通过3、失败0、未知1、环境无效0；v1旧W02保持未知，原件、分数和已发周报不覆盖。更新[阶段报告](reports/week2/stage-report.md)、[周报草稿](reports/weekly/2026-10-24-draft.md)和最多三项下周目标。仍没有外部人工复算反馈；该项为额外质量目标，不冒充导师硬性要求。
- 以下为同日第一批v1完成时的记录，当时新增2次；不与后续v2重复合计。
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
