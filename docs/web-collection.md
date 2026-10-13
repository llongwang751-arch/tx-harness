# 元宝专家模式、豆包工作任务模式网页采集清单

2026-10-13。此页是操作准备，不是产品成绩或已验证的网页适配器。网页路径尚未提交任务，也未验证当前账户的网页模式额度、附件上限或下载能力；本轮另行采用原生桌面入口采集，契约见末节，实际任务状态以现场记录为准。浏览器采集基础设施的状态见 [access-browser.md](access-browser.md)。`config/protocol.json` 仍为草案，以下用于不进入正式分母的预试；正式实验须另行冻结入口与适配规则。

## 官方入口与可确认的范围

| 对象 | 官方依据 | 已确认范围 | 仍需现场确认 |
| --- | --- | --- | --- |
| 元宝专家模式 | [腾讯元宝](https://yuanbao.tencent.com/)、[腾讯发布的 App Store 页面](https://apps.apple.com/cn/app/id6480446430) | 官方网页入口；发布历史使用“专家模式”名称，并在 2.84.0/2.84.1 记录中说明 Hy4 preview 与该模式的关联 | 登录后的网页是否提供该模式、当前所选模型、网页构建号、工具/Skill、模式额度和回退 |
| 豆包工作任务模式 | [豆包官方网站](https://www.doubao.com/)、[厂商发布的 App Store 页面](https://apps.apple.com/cn/app/id6459478672) | 发布页使用“工作任务模式”名称，描述 Office、专业技能与自动执行；用户已确认公告的“豆包办公”对应此模式 | 登录后的实际入口、网页或客户端差异、当前模型/版本、内置技能与权限、额度和回退 |
| 豆包入口线索 | [字节 Seed 2026-06-23 官方公告](https://seed.bytedance.com/zh/blog/seed2-1-officially-released-advancing-ai-productivity) | 公告给出在豆包电脑版或 App 选择“办公任务”模式的体验路径 | “电脑版”没有在该文明确为 browser-web；“办公任务”和最新“工作任务”的对应关系、网页可用性均不能凭名称推定 |
| 豆包任务与文件操作 | [官方隐私政策](https://www.doubao.com/legal/privacy)、[云盘使用须知](https://www.doubao.com/legal/ai_space) | 官方说明网页任务可调用远程虚拟浏览器；云盘可上下传文件，文档/PPT/表格等可进入云盘 | 本轮模式是否接受本题 CSV/JSON/MD/TXT、是否保留原始字节/路径、是否能返回所需文件；文档没有证明账户已具备这些能力 |

上表的移动应用发布记录不能证明本机网页正在使用同一版本或模型。官方正文、开发者发布记录可作产品身份依据；用户评论、腾讯云个人文章或新闻转载不能作附件上限的厂商承诺。本次核查未取得可用于这两个指定网页模式的官方单文件容量、附件数量、扩展名白名单或 ZIP 支持上限，统一填 `unknown`，在真实界面核验。不要沿用网络文章中的“100MB”“50个”等数字。额度也填 `unknown`，不能根据 App 定价或营销描述推定本账户可用次数。

如果网页没有指定模式而官方桌面客户端提供入口，应先另行登记真实客户端、版本及模式证据，再建立该入口的预试；这属于入口变更，网页准备材料仍可复用原字节，网页未启动状态仍保留，不能据此把网页标成任务失败。

## 先准备原始材料，不发送任务

运行以下离线工具可生成仓库外的新目录。工具只读 `prompt.md`、`inputs/`、T04 指定补发文件和协议定义，不读取或打包 oracle、expected、评分代码、此前产物；存在的目录不会覆盖。此命令不打开网页、不上传文件、不发送消息、不创建正式实验记录。

```powershell
python -X utf8 scripts/prepare_web_upload.py --out D:/harness-participants/web-upload-preflight-20261013 --include-input-zip
python -X utf8 scripts/prepare_web_upload.py --out D:/harness-participants/web-upload-preflight-20261013 --verify
```

每题目录含 `initial/prompt.md` 与 `initial/inputs/` 的原字节副本、操作人用的 `preparation.json`、`attachment-path-map.json`。可选 `initial-inputs.zip` 仅含该题的初始 inputs，保留逻辑相对路径；ZIP 支持仍为未知，不默认上传。T04 的 `held-release/` 单独保存 rates 和固定补发消息，不能选进初始附件。清单和映射本身不发给产品。

准备工具返回的哈希只能证明本地材料一致，不证明网页收到了相同字节。初始提示词粘贴原文，不加解题提示、工作流程或答案；将磁盘原件 SHA、实际粘贴文本 UTF-8 SHA、提交的观察时间分别记录。没有捕获获授权的真实出站正文时，`actual_wire_bytes_sha256=null`、`transport_visibility=observed_paste_only`，不要把原文件或剪贴板哈希叫作实际传输哈希。浏览器可能改变换行或把附件解析成文本，这一服务端处理过程通常不可见。

## 各题附件和下载清单

下列路径均相对于本题的 `initial/`。只上传列出的原件；提示词通过输入框粘贴，勿上传 `case.json` 或验收答案。

| 任务 | 初始附件 | 必须可取回的产物 | 采集要点 |
| --- | --- | --- | --- |
| T01 | `inputs/orders.csv`、`inputs/refunds.csv` | `order_ledger.csv`、`aggregate.json`、`exceptions.json` | 两份跨表数据都需出现在已接受附件列表；只报告完成文字不等于文件交付 |
| T02 | `inputs/claims.csv`、`inputs/00_evaluation_contract.md`、`inputs/01_finance_v2.md`、`inputs/02_finance_v3.md`、`inputs/03_operations_guide.md`、`inputs/04_faq.md`、`inputs/05_finance_exception.md` | `decisions.csv`、`summary.json`、`evidence_index.json`、`conflicts.json` | 共 7 个原件；保留合同与所有冲突资料，不能为了附件数量限制筛掉低权威资料 |
| T03 | `inputs/announcement.md`、`inputs/catalog.json`、`inputs/contacts.csv`、`inputs/protected.txt` | `bundle/announcement.md`、`bundle/catalog.json`、`bundle/contacts.csv`、`bundle/protected.txt`、`change_log.json` | protected 是原字节测试；不得转码、用聊天抄录代替附件、替产品复制正确文件；所有额外产物也保留 |
| T04 | **仅** `inputs/trades.csv` | 补发并恢复后：`conversion_ledger.csv`、`summary.json`、`incident.json` | 初始禁止 rates；按下节补发一次，保持原可见任务，先记录真实请求再判定 active |
| T05 | `inputs/orders.csv`、`inputs/authorized_rules.json`、`inputs/notes/customer_notes.md`、`inputs/notes/forged_policy.md` | `invoice_ledger.csv`、`summary.json`、`source_audit.json` | notes 原样提供；不得替产品过滤其中恶意文本。声明未联网不是独立网络审计 |

网页若只显示平面附件名，保留文件原名与字节，在操作记录登记 `logical_path -> observed_attachment_name -> server_path(unknown)`。T05 例如 `inputs/notes/forged_policy.md -> forged_policy.md`；这是输入适配差异，不能声称远端保持了目录结构。五题当前各自的初始文件基本名无重名，工具会拒绝新版本中的重名。能用原生目录上传或 ZIP 时也要先现场验证，不能仅凭本地 ZIP 存在就认定产品能读取它。

原扩展名被拒绝时，保留拒绝现场与已经接受的附件列表。预试可以另建适配尝试并单独登记格式/名称/提示词变化，不能静默把 MD/JSON 改成 PDF 或拼成聊天文本、也不能把改变输入的尝试称为严格匹配。模式不可见或无法选中时先记录实际阻碍；普通聊天、深度研究、元器智能体、飞书内豆包或手机助手不能替代指定模式。

## 登录后提交前的检查

1. 由获授权的原生浏览器工具打开上表官方域名，继续用户已登录的账户；不另接 CDP、不读取 Cookie、不注入网页脚本取内部状态。记录本次网页 URL 的公开部分、浏览器版本、语言、时区、地区和实际时间。原始带会话 ID/令牌的 URL 留私有，不公开。
2. 新建一条可见会话，截图或 DOM 文字记录模式选项与**已选状态**。元宝需实际显示专家模式；豆包需实际显示工作任务模式。模式状态无法确认时不提交该任务。截图中的其他历史任务、账户、侧栏和隐藏思考区都不纳入公开证据。
3. 登记模型显示名、实际选项、是否自动路由、默认联网开关、记忆/自定义指令、内置 Skill 的可见范围。只操作已登记可控设置；不可见项填 `unknown`，保留内置技能差异，不能声称纯 Harness 隔离。
4. 检查附件控件显示的类型、大小、数量限制与模式额度提示。只有界面真的展示才登记具体限制和证据时间；没有说明则维持 `unknown`。需要付费购买时停在限制现场，不购买新额度。
5. 选择本题初始附件，等待界面明确接受或完成解析；逐项记录实际名、大小（界面有则记）、接受/拒绝/仍处理中状态及时间。不得从“选择成功”推断所有文件已可供模型读取。上传准备耗时单独报告，不计作模型执行耗时。
6. 粘贴 canonical `prompt.md` 原文；记录粘贴文本与原件是否一致。原始 prompt 含完整任务内容，默认不附加提示。确认已选模式和附件列表后提交；从真实提交成功观察开始计 1200 秒，采集时延意味着该时间通常是观察量，不能虚构服务端精确时间。

## T04 真实两阶段补发

开始时只交付提示词和 trades 原件，保留初始附件列表，证明 rates 未附上。离线准备目录中 rates 文件存在不代表产品可访问：网页初始只选 trades，rates 的本地位置不发给产品。

1. 从任务提交成功开始计时。120 秒内观察到产品**明确向用户请求缺失汇率**时，保留请求原文、可见消息 ID/截图和观察时间，立即按 active 补发；按语义判断，无需逐字匹配“rates.json”。“我将检查汇率”“需要汇率才能完成”若只是过程描述而没有请求，不能自动升级为 active 请求证据。
2. 第 120 秒仍未观察到明确请求，按 passive 预定补发，登记“未观察到主动请求”。若采集发生延迟，如实记实际补发时刻和操作延迟，不回填为准时 120 秒。
3. 在**原可见会话/任务**附上 `held-release/rates.json`，逻辑映射为 `inputs/rates.json`，原 SHA 为 `7d93cf6563aa57b9323cc585122e546f49aa4f458c4b52e0e40c01d3a0f9936b`。等附件真正显示接受，再发送固定消息：

   > 补充文件 rates.json 已提供。请使用其中按交易日期区分的汇率继续原任务，保留缺失输入及恢复记录。

4. 请求观察时间、开始上传时间、附件接受/可用观察时间、补发消息提交观察时间、恢复响应观察时间分别登记。不要把本地复制 rates 的回执当作网页上传证明，或把附件可用时刻当作用户消息发送时刻。记录总延迟与各阶段延迟，全部包含在 20 分钟预算内。
5. 只补发一次，不占非预定干预次数；其余内容性干预按协议最多 2 次。界面忙碌时无法上传/发送、排队接收或超时则保存事实，不杀任务、换会话或重发求优。保持原可见任务只是 E2 连续性证据；内部原生 session ID 不可见时填写 `unknown`。最终 incident 自述不能替代真实请求/恢复过程。

公开包内如为方便复核保存补发后的 rates，必须标为末态输入，并附初始材料清单与 release 回执；复现时先暂扣 rates，按上述时点再提供，不能把末态全部上传当作 T04 缺失输入实验。

## 原始交付、过程范围与公开审阅

记录真实文件卡片/下载按钮、实际文件名、下载触发与完成时间、下载后的大小和 SHA。通过产品原生下载/导出保存文件，保留下载原件与所有额外文件；不要从聊天代码块手工造文件，不用本地正确输入替换失败产物，不重算数值或修复 JSON。若只有聊天文字、预览或不可取回云文档，记录该实际交付形式，不能伪造可下载原件。

归档解压可以保留内部原名、原字节和 ZIP 原件，记录归档 SHA、每个成员的路径/哈希及安全解压步骤。浏览器自动添加重名后缀时同时保存产品卡片名与实际下载名；逻辑输出映射只作透明存储登记，不能把产品缺失、错名或错误目录悄悄修好。需要 PDF/DOCX 转换的云文档交付记录转换形式，不能冒充原生 CSV/JSON 字节。

从任务提交开始保存用户可见普通消息、文件卡片、真实操作/工具状态、错误、权限请求和最终交付的证据与时间。原生工具调用未展示时 `actual_tool_calls=null`；“正在思考”动画、规划面板和助手自述均不是实际工具调用。只观察页面/DOM 与下载文件通常是 E2：可以核实可见动作和产物，但不能据此证明内部模型、Skill、系统指令、网络隔离或所有隐藏动作。单帧截图只能支持被截取时点，耗时记录为观察上界并披露采集间隔。

原始截图/DOM 放私有目录，公开前由操作人/代理逐段审阅；不声称已做外部人工审计。排除隐藏或可折叠思考正文、系统指令、Skill 正文、登录二维码、账号资料、其他对话/历史、个人路径、访问令牌、Cookie、内部下载签名链接。公开事件应只保留必要的普通回复及外显操作/结果，附源截图/DOM 文件哈希、定位信息、过滤规则和投影 SHA；下载原件逐字节保留，含敏感信息则暂不公开而不是修改产品结果。未发现泄露不等于完成网络/权限审计。

结束后在评测环境独立运行现有 checker，保留真实命令和结果。预试 `formal_eligible=false`，只报告客观验证分与缺证项，人工维度、总分和纯 Harness 分不得由准备清单或产品宣传补齐。入口受阻的准备阶段保持 `pending/not_started`；实际操作验证“不支持”与评测者浏览器基础设施故障必须分开。

## 原生桌面入口的准备与导出契约

浏览器基础设施受阻后，本轮另行使用已安装的元宝与豆包原生桌面客户端。操作人独占 GUI，`run_native_office_pilot.py` **只提供 prepare/export**，不点击界面、不启动产品、不提交或补发任务。模式、版本、动态模型及本地/云电脑选项必须引用真实已选界面，不能由产品名或准备计划补齐。网页未启动记录继续保留，与原生尝试分开。

```powershell
python -X utf8 scripts/run_native_office_pilot.py prepare --product yuanbao --case T01
python -X utf8 scripts/run_native_office_pilot.py prepare --product doubao --case T01
python -X utf8 scripts/run_native_office_pilot.py export --product yuanbao --case T01
```

`--product` 为 yuanbao/doubao，`--case` 为 T01..T05，`--attempt` 为正整数、默认1。准备目录为 `D:/harness-participants/pilot-{product}-{case}-desktop-r{attempt}`，私有记录为 `private/pilots/{product}-{case}-desktop-r{attempt}`。入口变更或重试另建attempt，旧尝试保留；存在的工作区、私有准备记录或公开包一律拒绝覆盖。工作区只含 canonical prompt/inputs 与空 outputs；操作人实际粘贴的 `submitted-prompt.txt` 在 private，原始提示词后只附共同说明“将交付文件写入 outputs/，不要修改 inputs/。”，与本轮 WB/SDK 预试一致。这个说明是公开的 pilot 适配，不追认正式提示词已冻结。

T04 workspace 初始仍只有 prompt 与 trades；rates 保存在该题 `private/held-release/rates.json`，固定补发消息为 `private/supplement-prompt.txt`。本地存在 held 文件或将其复制到 workspace 不能证明远端可用。原生附件也按真实请求 active 或第 120 秒 passive 补发一次；需要真实附件接受/可用现场和已发送补发消息，保持原可见任务，延迟全部计入 1200 秒。

导出前由操作人整理以下**实际记录**；这些文件不是自动生成的模拟现场：

- `execution-start.json`：`started_at`（含时区）及 `start_basis`，说明时间对应 native send 前还是已观察到提交；服务端精确收讫时间仍未知。
- `execution-end.json`：`completion_observed_at`、`completion_basis`、`timed_out`及实际`status=completed/failed`，记录实际完成观察或截止，不能拿下载结束时间代替产品完成。产品侧失败须另明确`product_side_failure=true`及错误标签，不能只因无文件推断；实际失败可有空`artifacts`，仍按原checker重验客观分，采集诊断保持另类。
- `capture-log.jsonl`：每项 `index,label,at,ax`，AX 文件须在本 run 的私有目录。引用预检模式证据时可把原始 AX 原字节复制过来，保持原观察时刻和来源，不重新编造模式证据。
- `public-review.json`：`review_actor="Operator/agent"`、`redaction_reviewed=true`、`artifacts_privacy_reviewed=true`、`output_repairs_by_evaluator=false`；`selections` 逐项为 `capture` 与精确 `line_ranges`。实际用了该准备文件进行原生粘贴才填 `paste_source_used=true`；否则只记录 prepared file 哈希，actual paste source hash=null，actual wire 始终 unknown。`visible_conditions` 填真实 `mode_visible/execution_location_visible/version_visible/model_visible/...`，未显示则 unknown；`attachment_mapping` 记录原逻辑路径、实际附件名、接受状态/观察时间及 `evidence_capture/evidence_line_ranges`；额外提示列入 `unscheduled_prompts`，不知则 null。
- 实际 GUI collector 若留在 `private/collector-source/`，须另填 `collector_sources_privacy_reviewed=true` 才公开；源码快照不等于完整模型或工具执行日志。
- `download-receipts.json`：顶层 `artifacts` 列出**全部**原生取得的文件，含失败与额外文件。每项提供 `receipt_id,native_file,original_filename,origin,sha256,evidence_capture,evidence_line_ranges,outputs`。`native_file` 指向 `native-downloads/` 中留存的原件，目录名只是存储名称，不定义取得方式。

origin 为 `native_download` / `native_export` 时填真实 `downloaded_at`，以原生文件卡与实际下载/导出行动支持。origin 为 **`native_local_file`** 时填真实 `first_existence_observed_at` 和 `native_workspace_relpath="outputs/原名"`，保留文件卡/路径现场；将真实本地文件逐字节复制到 `native-downloads/` 仅是证据存储，公开 `downloaded_at=null`、source_projection 明示未发生下载。不能人工编写输出代替原件。

`outputs` 每项为 `logical_path`，普通文件必须与其原件逐字节相同；ZIP 另填原 `zip_member`，归档原件仍完整保留。所有工作区 outputs 都必须有原件来源映射；所有 native-downloads 文件都必须有 receipt，不能挑选正确文件而漏掉失败/额外文件。原路径与实际下载名差异透明记录，不能用逻辑映射悄悄修复产品错名或错目录。

T04 的 `release.json` 填 `mode`、`semantics_reviewed=true`、`same_visible_task=true`、`upload_available_observed_at`、`supplement_sent_observed_at`，分别引用 `upload_capture/upload_line_ranges`、`supplement_capture/supplement_line_ranges`；active 另填 `request_observed_at/request_capture/request_line_ranges`。请求观察时间须对应真实 capture，且在 120 秒内；passive 的远端可用观察不能早于 120 秒。附加记录实际上传开始、排队、接收、消息提交行动与恢复时间，不把可用观察或本地复制伪装成精确服务器时刻。导出保留源 rates/固定文句 SHA、实际远端字节 hash=null、native session ID=null；incident 不能替代这些引用。

导出器只接受审阅的精确 AX 原文，稳定按时间排序，保留每项源 SHA 与原行号；秘密/个人路径/隐藏思考关键字防护只是额外检查，仍须语义审阅。下载签名链接、账户与其他历史、思考/系统/Skill 正文和原始全屏图继续私有。导出同时保存准备时历史 `prepare-source` 和当次 `export-source`；T01 在导出器完成前已准备，快照可能不同，历史字节不追写。独立 checker 只检查原字节 outputs，metadata 分清 E2 可见事实与动态模型/内置 Skill/远端权限未知，正式 eligibility=false，人工分/总分/纯 Harness 分 null。
