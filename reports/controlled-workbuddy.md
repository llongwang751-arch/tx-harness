# WorkBuddy 固定响应校准复核

李明远，2026-10-25 归档。三次任务实际执行于 2026-10-24 凌晨（北京时间），本次只整理已有记录，没有重开产品或补跑任务。

**三次独立任务均已被原生客户端接受，但没有一次完成共享工具契约：通过 0、未知 3、产品失败 0。** 它们是接入校准，不是三次正式对照，也不能把校准器的 HTTP 错误算成 WorkBuddy 的业务失败。[机器审计及逐项检查](controlled-workbuddy.json)由[审计脚本](../scripts/audit_controlled_workbuddy.py)生成。

## 任务、配置和实际现场

测试入口为 WorkBuddy V5.8.3 桌面客户端，使用官方 Computer Use。自定义模型 `fixed-tool-v1` 指向本地固定响应服务，不进行真实模型推理；共享 MCP、固定参数和 125 字节目标产物沿用 Codex、DSH 对照的来源。工具调用及自定义协议已开启。已有插件、系统上下文和原生工具发现流程仍保留，没有宣称完整关闭 Skill。

输入均为各轮冻结的 `prompt.txt`。完成条件不止“服务收到请求”：必须实际派发相同 probe 参数、收到共享 MCP 回包、正确交付产物，并在原生任务中正常结束。三轮均未达到这些条件。

| 任务、预登记 | 公开现场 | 实际收到的模型请求 | 观察到的停点 | 结论及置信依据 |
|---|---|---|---|---|
| WBC00，01:45，`c18fd84` | [证据清单](../public/supplements/controlled-workbuddy-v1/WBC00-workbuddy-calibration/manifest.json)、[原生任务摘录](../public/supplements/controlled-workbuddy-v1/WBC00-workbuddy-calibration/gui-scene.json)、[规则与输入登记](../supplements/controlled-workbuddy-v1/calibration.json) | 2；固定辅助回复 0 | 固定适配器产生传输错误，原生界面出现错误及重试入口；未点击重试 | 接入未知。任务接受、错误界面及请求数有对应记录；共享 probe 未实际调用，无法判断产品契约能力 |
| WBC01，01:53，`9d51461` | [证据清单](../public/supplements/controlled-workbuddy-v2/WBC01-workbuddy-calibration/manifest.json)、[原生任务摘录](../public/supplements/controlled-workbuddy-v2/WBC01-workbuddy-calibration/gui-scene.json)、[规则与输入登记](../supplements/controlled-workbuddy-v2/calibration.json) | 2；固定辅助回复 1，拒绝事件 1 | 后一请求声明 23 个内置工具，包括 ToolSearch，未声明目标 probe；适配器拒绝，原生界面报错 | 接入未知。工具名称和 schema 摘要可查；不能由“初始请求未声明”推出“产品没有 MCP 工具能力” |
| WBC02，02:01，`6d86cd4` | [证据清单](../public/supplements/controlled-workbuddy-v3/WBC02-workbuddy-calibration/manifest.json)、[原生任务摘录](../public/supplements/controlled-workbuddy-v3/WBC02-workbuddy-calibration/gui-scene.json)、[规则与输入登记](../supplements/controlled-workbuddy-v3/calibration.json) | 4；固定辅助回复 1，拒绝事件 3 | 固定 ToolSearch 参数未通过适配器 schema 校验，后续请求继续被拒绝；本地服务在 120 秒任务期限结束 | 接入未知、原生终态未知。接受证据为实际任务消息、处理中状态、停止按钮及端点活动；最终窗口最小化，未观察到原生完成 |

三轮共享 probe 的实际 MCP 调用均为 0、产物均为空。WBC02 的 ToolSearch **派发数同样为 0**；看到声明不等于调用成功。WBC02 的 3 条拒绝与 3 条传输错误是同一批请求的不同事件，不能相加为 6 次任务。后两个请求的重试发起者未被观察，不把它归因为人工或产品自动重试。

## 能确认什么，仍不能确认什么

可以确认原生任务到达了自定义模型端点；公开的 MCP 日志保留 initialize 和 tools/list 事件，但它们没有进一步发展为 probe 调用。WBC01 的声明形态为增加显式发现阶段提供了线索，WBC02 已检验该固定桥接方案，结果仍被适配器拒绝。当前只有 ToolSearch schema 摘要，不能据此认定是哪项 schema 约束导致拒绝，更不能直接归责于产品。

固定响应排除了这几次调用中真实模型选工具、改参数的随机性。它不能证明默认模型的能力，也没有独立测出全部 Skill 的影响。WorkBuddy 的辅助请求、发现阶段与 Codex、DSH 的完整调用链不同；共享子链尚未实际打通，不能给出五款同条件排名。

## 未知的后续和停止条件

本轮每版只登记一个新任务，前版未知保留，没有运行中放宽规则。下一步若继续，应先独立登记一个只保留工具名称及 schema 约束的诊断，明确请求上限，再验证固定参数为何被拒绝。只有取得足够声明证据才重开接入校准；若仍无法安全取得，则停止共同端点实验，保留适配未知。正式成功／报错两组对照须等校准通过后另行登记，不能由这三次补算。

WBC02 的服务结束早于用户暂停记录。期限只关闭本地 HTTP 服务，没有终止桌面客户端；原生任务是否结束仍未知。这一观察缺口与接口不兼容分开保留。

## 复核范围和命令

公开包使用字段白名单导出，含逐文件 SHA、原始记录摘要及人工审阅的任务相关 AX 摘录；没有公开原始 AX、账号／会话信息、密钥、系统提示、Skill 正文或任意工具输出。原始画面留在私有目录，摘要只支持持有人核对，不能替代独立观察者。校准结果的置信范围是记录一致性，不是第三方重复实验。

在仓库根目录执行：

```powershell
python -X utf8 scripts/audit_controlled_workbuddy.py --output reports/controlled-workbuddy.json --check
python -X utf8 -m unittest tests.test_controlled_workbuddy_audit -v
```

审计仅读取公开包、冻结规则及 Git 历史；8 个离线测试覆盖原生接受准入、未知终态、请求计数、字段脱敏、登记哈希篡改和禁止覆盖。三轮各算一次产品任务；工具调用、HTTP 请求、界面检查和校准器单元测试均不另计产品运行。
