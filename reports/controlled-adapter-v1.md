# 固定动作下的工具契约实测

作者：李明远。2026-10-24。正式登记提交：[`1a03e16`](https://github.com/llongwang751-arch/tx-harness/commit/1a03e16)。[规则与停止条件](../supplements/controlled-adapter-v1/protocol.md)、[机器登记](../supplements/controlled-adapter-v1/protocol.json)、[现场索引](../public/supplements/controlled-adapter-v1/README.md)、[逐项复算JSON](controlled-adapter-v1.json)。

这次在真实Codex CLI和DSH SDK上运行了共同的固定动作，四个正式任务均满足预定工具契约。固定响应服务代替神经模型，两个产品确实通过各自MCP客户端执行了工具，再把真实结果传回。这个方法解决了这条调用路径上的生成随机性和Skill文本改变动作的问题，不能据此声称五款商业产品都已统一模型或全部禁用Skill。

## 为什么增加这一条轨道

原五产品业务题和S01都让模型自行决定动作。即使最后文件相同，也无法分清模型选择、Skill和Harness各起了多少作用。这次把动作先固定下来，只观察收到规定动作后发生的事情。服务没有能力理解任务或Skill：第一次返回冻结工具名和参数，第二次收到同一call_id对应的工具回包后固定结束；多一次请求、错误调用ID或伪造回包均拒绝。

正式任务只有四次，各产品各一个成功臂和错误臂。顺序在执行前冻结为DSH错误、Codex成功、DSH成功、Codex错误。每次使用空目录和新配置，不复用账户，上一实例结束后才启动下一次。所有登记测试PID在收集时均已退出。固定端点只监听127.0.0.1；这表示本次推理配置没有调用外部模型，不是对整个操作系统的网络审计。

## 实测结果及判分

各项通过为1、不符合为0、证据不足为null，不加总为产品名次。错误臂产生预期错误、保持回包并正常结束，属于契约通过。规则在正式运行前冻结；离线判卷脚本在采集后实现并接受反例测试，不冒充事前盲审。

| 正式任务 | C1真实调度及参数 | C2文件/错误效果 | C3回包内容 | C4正常终止 |
|---|---:|---:|---:|---:|
| [CA11 DSH错误](../public/supplements/controlled-adapter-v1/CA11-dsh-error/manifest.json) | 1 | 1 | 1 | 1 |
| [CA12 Codex成功](../public/supplements/controlled-adapter-v1/CA12-codex-success/manifest.json) | 1 | 1 | 1 | 1 |
| [CA13 DSH成功](../public/supplements/controlled-adapter-v1/CA13-dsh-success/manifest.json) | 1 | 1 | 1 | 1 |
| [CA14 Codex错误](../public/supplements/controlled-adapter-v1/CA14-codex-error/manifest.json) | 1 | 1 | 1 | 1 |

成功臂文件均为125字节，SHA-256为`a21822b8b21b9991cec154040fb574fd9dd33ca326caf79c04b208aa3d9d530d`，包含中文、emoji、CRLF/LF和连续空格；文件按实际字节收集。错误臂MCP返回`isError=true`与`E_FIXTURE_DENIED`，没有产物文件。四臂各有一次真实tools/call、两次端点请求和正常原生终止，没有用工具次数增加独立运行数。

可见差异是错误的包装方式：DSH的模型侧回包文本加了`Error:`前缀，普通工具事件状态为`error`；Codex回包使用两段content，普通事件状态为`failed`。固定错误对象均保留。两款普通事件都没有独立暴露isError布尔，模型侧也未见独立布尔字段，不能从最终结束文字推断完整错误类型映射。Codex普通事件提供item_id，DSH提供call_id；没有把Codex的item_id伪装成模型call_id。端点回包中的调用ID另有实际记录。

## 校准失败也保留

校准共五次启动尝试，三次进入真实任务：两次通过、一次适配器未知。另两次在接受任务前配置解析失败，不算独立产品任务。

| 尝试 | 是否进入任务 | 观察和处理 |
|---|---|---|
| CA00 Codex | 否 | 我写的TOML数组序列化错误；保留原错误及登记版本 |
| CA00 DSH | 是 | 同一固定工具链路通过 |
| CA01 Codex | 否 | 使用了当前版本不支持的配置字段；删除该字段，原尝试保留 |
| CA02 Codex | 是 | MCP自动审批模式未放行写工具；真实调用未到服务端，记校准未知 |
| CA03 Codex | 是 | 单次配置显式批准唯一固定工具后通过；没有扩大文件沙箱 |

校准修订各自先登记推送再执行，没有覆盖失败文件。CA02能定位到审批配置，但不据此宣称产品能力失败；正式协议只在两入口都校准后登记。全部校准和正式任务合计九份包、七次已接受任务，有效通过六、未知一；正式四臂分母独立，不能把校准成功加入正式通过率。

## 归因能推进到哪一步

| 因素 | 本次做法 | 实际证据与保留项 |
|---|---|---|
| 模型 | 用同一固定程序产生同一canonical工具动作，没有神经推理 | 源码与冻结参数SHA、两种端点的请求记录；不是同一个真实模型能力比较 |
| Skill | DSH单次关闭filesystem/Office提供器、Skill工具、agent-instructions；Codex隔离配置并关闭已知发现与扩展 | Codex仍观察到目录标题，不能写“全部删除”；固定程序忽略Skill文本，实际调用与固定动作逐项核对 |
| Harness链路 | 真正客户端接收动作、调度MCP、传参、回传、终止 | 服务端请求/返回与普通产品事件相互对应，成功文件由工具实际写入 |
| 工具 | 两产品使用同一源码、schema和参数对象 | 产品对schema/工具名的规范化及wire codec仍不同，原包装分别保留 |
| 环境 | Windows、串行、新目录，官方版本和exe摘要冻结 | Codex 0.159.2、DSH 0.2.1-rc.2；DSH不是旧S01的0.2.0-rc.2，不混入旧分 |

现象是相同预定动作在两款真实Harness上均完成调度和回传。原因线索是把生成过程替换为固定程序后，工具路径仍可独立执行。已验证结论是这四个指定任务满足共同工具契约。系统上下文、内置工具目录、协议适配、其它状态管理均未被统一；没有给出跨产品纯因果数值或复杂办公能力排名。

共同MCP属于可信宿主工具，文件效果绕开原生文件沙箱。因此这批文件不能证明产品权限防护，已有S02权限对照仍单独解释。错误臂也没有测试自主修复，固定程序只结束任务。

标题观察来自请求中对Skill相关标题的正则检测，不证明某个具体Skill已装载或执行；本轮没有读取其正文。模型元数据回退告警也保留在Codex普通场景中，不能据此给固定端点附会真实模型能力。

WorkBuddy、元宝专家、豆包工作任务仍在五产品真实任务轨道，本轮未验证其共同provider接口。后续每款最多一次正式接口核查，有新的可用接口才登记实验；无入口证据便停止对该路径的推论，不重复业务题来凑控制条件。

## 依据和复核

每包包含规则提交指针、实际启动配置投影、execution、model-events、mcp-events、普通场景及原件清单。报告JSON逐项列证据文件、判定理由、失败检查、置信范围，并核对历史提交中的协议与源码摘要；原始系统提示、Skill正文、SDK原始wire和环境变量值不公开。环境值仅留变量名和摘要。

上述结论对公开字节和指定契约的一致性为高置信：固定动作、真实MCP记录、端点结果、普通终止与原件可以交叉检查。原始现场仍由单一操作方在AI辅助下收集，尚无外部人工复核，不能用哈希替代现场真实性证明。

```powershell
python -X utf8 scripts/audit_controlled_adapter.py --check
python -X utf8 -m unittest tests.test_controlled_model_fixture tests.test_controlled_probe_mcp tests.test_controlled_adapter_audit -v
```

这些命令只读公开包，不启动产品。真实执行入口为[run_controlled_adapter.py](../scripts/run_controlled_adapter.py)，服务为[固定响应](../scripts/controlled_model_fixture.py)与[MCP工具](../scripts/controlled_probe_mcp.py)。历史ID拒绝覆盖；新环境需新登记和新ID。

Codex支持的配置入口参照[官方配置说明](https://learn.chatgpt.com/docs/config-file/config-reference)和[MCP配置说明](https://learn.chatgpt.com/docs/extend/mcp)；DSH入口来自已安装官方SDK的只读接口核查，具体文件SHA和行范围见[来源登记](../supplements/controlled-adapter-v1/interface-sources.json)。介绍文档只说明入口依据，执行结果仍以现场为准。
