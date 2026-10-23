# 五产品模型、Skill与Harness归因边界核对

作者：李明远。核对日期：2026-10-23。本次为既有公共证据的离线审计，新增产品运行0次；S01五产品各3轮共15轮被复核，不重算成本周新增。

当前证据支持端到端结果、具体请求边界和有限的产品内操作对照；五产品后台模型与完整Skill条件没有匹配，纯Harness因果分保持null。判断范围逐项列出，不能只靠报告末尾的限制说明。

字段定位、源SHA、三轮配置与全部分母见[审计JSON](attribution-boundaries.json)和[逐产品评审记录](../supplements/attribution-audit-v1/assessment.json)。源文件固定为[b8cd4f9](https://github.com/llongwang751-arch/tx-harness/commit/b8cd4f95e7036e1fd35102fc5e96e430d44e5105)已有字节；当前官方配置说明不追认为旧实验已生效。

| 产品 | 模型条件 | Skill条件 | 证据入口 |
|---|---|---|---|
| Codex | 三轮请求gpt-6.1-sol；CLI 0.159.2；实际后台部署与effort未独立验证。 | 启动配置跳过host Skill discovery，关闭plugins/hooks/memories/apps并限制项目文档；内置指令和后台Skill仍未知，不能写成无Skill。 | [r1](../public/supplements/contracts-v2/S01-codex-r1/review.json)、[r2](../public/supplements/contracts-v2/S01-codex-r2/review.json)、[r3](../public/supplements/contracts-v2/S01-codex-r3/review.json) |
| WorkBuddy | S01三轮V5.8.2、办公、Deepseek-V4.1-Flash标签；不能与旧业务题5.7.7或窗口v2预检5.8.3混成同一批配置。 | S01前两轮skills_state为null，第三轮没有完整Skill清单；窗口v2只记录未主动安装/调用，隐藏或自动Skill未排除。 | [r1](../public/supplements/contracts-v2/S01-workbuddy-r1/review.json)、[r2](../public/supplements/contracts-v2/S01-workbuddy-r2/review.json)、[r3](../public/supplements/contracts-v2/S01-workbuddy-r3/review.json) |
| DSH（DeepSeek Harness） | 官方桌面捆绑SDK 0.2.0-rc.2，请求deepseek-account/deepseek-flash、high；不是已鉴定的后台部署。 | includeDefaultRoots=false、watch=false只关闭用户/项目发现，保留Office及诊断Skill；r2/r3有实际Skill调用元数据，不能写全部关闭。 | [r1](../public/supplements/contracts-v2/S01-dsh-r1/review.json)、[r2](../public/supplements/contracts-v2/S01-dsh-r2/review.json)、[r3](../public/supplements/contracts-v2/S01-dsh-r3/review.json) |
| 元宝专家模式 | 专家模式原生菜单显示Hy3；r2标签依赖截图而非AX；S01数值版本及后台部署未知。 | 内置Skill和真实工具参数未知，没有加载清单或已生效的全禁用证明。 | [r1](../public/supplements/contracts-v2/S01-yuanbao-r1/review.json)、[r2](../public/supplements/contracts-v2/S01-yuanbao-r2/review.json)、[r3](../public/supplements/contracts-v2/S01-yuanbao-r3/review.json) |
| 豆包工作任务模式 | S01工作任务→云电脑，提交时显示自动 低；不是可核验的具体底模版本；数值版本缺证。 | 公开metadata明确内部模型、Skill、工具和网络未验证；未提供完整Skill禁用/加载证明。 | [r1](../public/supplements/contracts-v2/S01-doubao-r1/review.json)、[r2](../public/supplements/contracts-v2/S01-doubao-r2/review.json)、[r3](../public/supplements/contracts-v2/S01-doubao-r3/review.json) |

## 全部尝试与条件分母

下表每产品实际进入的S01任务均为3轮。单元格为“通过/eligible；未知；上游偏离”。未知和未进入条件不是产品失败；不得只保留形成正确请求的片段。请求能否形成本身可能受Harness影响，条件分母不是随机抽样，不能跨产品按这张表排名。

| 产品 | 输入读取 | 缺失目标反馈 | literal写保真 |
|---|---|---|---|
| Codex | 3/3；未知0；偏离0 | 1/1；未知2；偏离0 | 0/0；未知3；偏离0 |
| WorkBuddy | 0/0；未知3；偏离0 | 0/0；未知3；偏离0 | 0/0；未知3；偏离0 |
| DSH（DeepSeek Harness） | 3/3；未知0；偏离0 | 2/2；未知0；偏离1 | 3/3；未知0；偏离0 |
| 元宝专家模式 | 0/0；未知3；偏离0 | 0/0；未知3；偏离0 | 0/0；未知3；偏离0 |
| 豆包工作任务模式 | 0/0；未知3；偏离0 | 0/0；未知3；偏离0 | 0/0；未知3；偏离0 |

这些S01内部指标的环境有效性和适用性并未逐轮独立证明；JSON同时保留相应未证实计数。CLI/SDK命令、独立读取工具与GUI下载并非同一种工具契约。五产品S01均实际取得3份echo与3份receipt，字节/声明验收与内部请求证据分别报告。

## 每款产品的结论与停止条件

### Codex

**现象：**S01三轮取得相等echo与合规receipt；普通命令可支持部分读请求与返回，完整literal写载荷仍缺证。

**原因线索：**读取、变量写文件和异常捕获属于不同层次；父命令成功不等于其中每个文件读取都成功。

**已验证结论：**支持已记录输入读取和S02指定配置中的写权限行为；不证明后台模型一致或五产品纯Harness优势。

**置信依据：**公开原件、登记版本、字段定位和判定可复算；界面/请求来源仍依赖单一操作方与AI辅助采集，未收到外部人工复算反馈。

**下一步：**仅在新接口能提供有效部署、Skill清单和同一工具契约的证据时，另登记最小单因素对照。已有三组权限对照先作为局部证据复核。

**停止条件：**没有新增生效证据时停止追加相同请求或同名模型试跑；后台归因保持未知。

### WorkBuddy

**现象：**S01三轮原件验收通过，内部三项E1缺证；新窗口v2在续接前直接取回原附件与既有交付。

**原因线索：**原生直接另存发生在续接前，主观察不依赖新的操作方模型提交；主机源文件和本地原件始终存在。

**已验证结论：**支持本次可见界面与本地文件取回；不证明云端附件保存、后台上下文完整或普遍恢复可靠性。

**置信依据：**公开原件、登记版本、字段定位和判定可复算；界面/请求来源仍依赖单一操作方与AI辅助采集，未收到外部人工复算反馈。

**下一步：**只在官方导出能区分本地主机指针与独立存储，或能显示有效模型/Skill配置时再预检并登记。

**停止条件：**保留当前v2结论与v1未知，不重复关窗来凑通过率；没有新的正式证据入口则停止本批更强归因。

### DSH（DeepSeek Harness）

**现象：**S01三轮读与literal写契约成立；缺失目标反馈两轮进入条件并通过，另一次请求目标偏离。

**原因线索：**明确请求载荷、普通结果和原件可对应，能定位请求到文件这一段；ACL错误仍有环境或执行器解释。

**已验证结论：**支持已观察边界中的请求/结果及写入一致；未进入缺失目标条件的一轮仍保留，不以2/2推总体恢复率。

**置信依据：**公开原件、登记版本、字段定位和判定可复算；界面/请求来源仍依赖单一操作方与AI辅助采集，未收到外部人工复算反馈。

**下一步：**未来仅在正式入口能核实全部Skill范围与实际加载版本后，再考虑开关消融；须保留无Skill臂和有Skill臂的生效证明。

**停止条件：**只有includeDefaultRoots关闭而内置Skill仍保留时停止宣称Skill已隔离；不读取额外Skill正文来补模型身份。

### 元宝专家模式

**现象：**S01三轮下载原件字节/声明验收通过；输入读取、错误状态映射与literal写入三项内部E1均缺证。

**原因线索：**助手表述、模式标签、附件卡和最终下载分别证明不同层次，不能互相代替真实工具请求。

**已验证结论：**支持这些原生下载与固定文件验收事实；不能认定内部没有读写工具、没有Skill或与其他产品模型匹配。

**置信依据：**公开原件、登记版本、字段定位和判定可复算；界面/请求来源仍依赖单一操作方与AI辅助采集，未收到外部人工复算反馈。

**下一步：**仅检查受支持的有效配置或普通请求/结果导出；若提供则先核对是否完整、可绑定当前任务。

**停止条件：**正式导出仍不能提供内部配对记录时保留E2，不靠重复截图或相同提示词升级E1及独立归因。

### 豆包工作任务模式

**现象：**S01三轮原生下载原件通过；三项内部E1缺证；云电脑入口与本地失败预试分别保留。

**原因线索：**自动档位只描述可见选择，正确原件不足以反推模型身份、内部执行参数或Skill状态。

**已验证结论：**支持该云电脑入口的原件交付事实；不支持网络隔离、纯Harness因果分或内部机制排名。

**置信依据：**公开原件、登记版本、字段定位和判定可复算；界面/请求来源仍依赖单一操作方与AI辅助采集，未收到外部人工复算反馈。

**下一步：**只在正式配置/导出能给出固定底模、Skill生效清单或普通请求结果后，登记最小验证任务。

**停止条件：**仅有自动档位和聊天自述时停止更强归因，不把无法提供内部证据记为产品失败。

## 已完成的局部验证与仍未满足的控制

[Codex三组权限对照](permission-pairs-v2.json)支持记录条件下的目标写入/拒绝；[WorkBuddy窗口v2](window-reopen-v2.md)支持续接前的原生消息与本地原件取回。它们不表示隐藏Skill、后台模型或工具实现已全部隔离，单对照也不足以估计普遍因果效应。

DSH r2/r3确有Skill调用元数据；r2曾因事件投影意外暴露一份Skill正文，公开投影随后移除。不能声称评测方全程未接触Skill正文或已完成盲评；r3在审阅前排除了正文。这是评测过程限制，不作为产品失败或新运行。

## 是否需要立即重跑五款

本次已公开源未提供新的、可操作且能核验生效的共同模型/全部Skill配置；先交付逐产品审计，不提交重复任务。

只有取得能改变具体判断的新证据，才重新打开实验：

1. 正式接口可在同一参评入口核验实际模型部署及参数。
2. 完整Skill启用/加载范围可核验，或固定完整Skill版本。
3. 工具、上下文、环境匹配且只改变一个预定因素。
4. 先登记输入、预算、随机配对顺序、全部尝试与停止条件。

若官方允许替换模型适配器，可另登记确定性请求/响应的组件契约实验；它研究该受控入口，不把自建代理、模拟回合或另一API冒充原商业产品。当前未确认五产品都支持同一适配接口，不据此启动或声称完成这种实验。

未来配置预检依据当前[官方OpenAI配置文档](https://learn.chatgpt.com/docs/config-file/config-reference)核对单项Skill开关，并按[Skill装载说明](https://learn.chatgpt.com/docs/build-skills)检查隐式调用及仓库、用户、管理和系统来源；配置选项存在不证明旧CLI已生效。产品运行与模型共同作用的评测边界参见[Anthropic方法说明](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)；可控条件分组与随机化参见[NIST实验设计](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm)。这些来源提供方法，不代替本项目现场。

复核：`python -X utf8 scripts/audit_attribution_boundaries.py --check`。该命令不启动产品，不修改旧包、旧分或已发周报；一致性检查不等于独立现场认证。
