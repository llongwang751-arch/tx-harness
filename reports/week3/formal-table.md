# 正式比较表（由台账生成）

本页由 `python -X utf8 scripts/ledger.py build` 从 `ledger/runs.jsonl` 直接生成，不手工编辑。纳入条件：`account=product_run` 且规则冻结、题面有效、证据有效、无污染。未知裁定不计分、不记失败，也不从已评部分折算满分。表内“产物分”是 0–60 的文件契约分，不含人工过程维度。

- 产品运行记录：47（端到端 25、固定响应主臂 4、接入校准 6）
- 通过四道门槛：29；被门槛挡下：0；未知裁定：5

## 五题端到端：逐产品汇总

| 产品 | 运行 | 已评 | 通过 | 失败 | 未知 | 门槛挡下 | 产物分 | 缺题 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Codex | 5 | 5 | 5 | 0 | 0 | 0 | 300/300 | 无 |
| WorkBuddy | 5 | 5 | 5 | 0 | 0 | 0 | 300/300 | 无 |
| DSH | 5 | 5 | 4 | 1 | 0 | 0 | 270/300 | 无 |
| 元宝专家模式 | 5 | 5 | 1 | 4 | 0 | 0 | 159/300 | 无 |
| 豆包工作任务模式 | 5 | 5 | 5 | 0 | 0 | 0 | 300/300 | 无 |

排名：**不发布**（`null`）。原因：

- Codex: backend model identity unattested
- WorkBuddy: backend model identity unattested
- DSH: backend model identity unattested
- 元宝专家模式: backend model identity unattested
- 豆包工作任务模式: backend model identity unattested
- protocol state of the 25 end-to-end runs is draft_before_pilot, not a preregistered frozen protocol

## 五题端到端：逐次记录

| 产品 | 题 | 运行 | 裁定 | 产物分 | 证据等级 | 门槛 |
|---|---|---|---|---:|---|---|
| Codex | T01 | `codex-T01-r1-attempt02` | pass | 60 | medium | ✓✓✓✓ |
| Codex | T02 | `codex-T02-r1-attempt01` | pass | 60 | medium | ✓✓✓✓ |
| Codex | T03 | `codex-T03-r1-attempt01` | pass | 60 | medium | ✓✓✓✓ |
| Codex | T04 | `codex-T04-r1-attempt02` | pass | 60 | medium | ✓✓✓✓ |
| Codex | T05 | `codex-T05-r1-attempt01` | pass | 60 | medium | ✓✓✓✓ |
| 豆包工作任务模式 | T01 | `doubao-T01-desktop-r2` | pass | 60 | high | ✓✓✓✓ |
| 豆包工作任务模式 | T02 | `doubao-T02-desktop-r1` | pass | 60 | high | ✓✓✓✓ |
| 豆包工作任务模式 | T03 | `doubao-T03-desktop-r1` | pass | 60 | high | ✓✓✓✓ |
| 豆包工作任务模式 | T04 | `doubao-T04-desktop-r1` | pass | 60 | high | ✓✓✓✓ |
| 豆包工作任务模式 | T05 | `doubao-T05-desktop-r1` | pass | 60 | high | ✓✓✓✓ |
| DSH | T01 | `dsh-sdk-T01-r1` | pass | 60 | high | ✓✓✓✓ |
| DSH | T02 | `dsh-sdk-T02-r1` | pass | 60 | high | ✓✓✓✓ |
| DSH | T03 | `dsh-sdk-T03-r1` | pass | 60 | high | ✓✓✓✓ |
| DSH | T04 | `dsh-T04-r1` | pass | 60 | high | ✓✓✓✓ |
| DSH | T05 | `dsh-sdk-T05-r1` | fail | 30 | high | ✓✓✓✓ |
| WorkBuddy | T01 | `workbuddy-T01-desktop-r1` | pass | 60 | high | ✓✓✓✓ |
| WorkBuddy | T02 | `workbuddy-T02-desktop-r1` | pass | 60 | high | ✓✓✓✓ |
| WorkBuddy | T03 | `workbuddy-T03-desktop-r1` | pass | 60 | high | ✓✓✓✓ |
| WorkBuddy | T04 | `workbuddy-T04-desktop-r1` | pass | 60 | high | ✓✓✓✓ |
| WorkBuddy | T05 | `workbuddy-T05-desktop-r1` | pass | 60 | high | ✓✓✓✓ |
| 元宝专家模式 | T01 | `yuanbao-T01-desktop-r1` | fail | 42 | high | ✓✓✓✓ |
| 元宝专家模式 | T02 | `yuanbao-T02-desktop-r1` | fail | 27 | high | ✓✓✓✓ |
| 元宝专家模式 | T03 | `yuanbao-T03-desktop-r1` | fail | 0 | medium | ✓✓✓✓ |
| 元宝专家模式 | T04 | `yuanbao-T04-desktop-r1` | pass | 60 | high | ✓✓✓✓ |
| 元宝专家模式 | T05 | `yuanbao-T05-desktop-r1` | fail | 30 | high | ✓✓✓✓ |

门槛顺序为：规则冻结 / 题面有效 / 证据有效 / 无污染。

## 固定响应工具契约（受控组件轨道）

模型响应由本地脚本固定，无神经推理；四臂同一工具、同一参数。

| 产品 | 运行 | 模式 | 裁定 | 证据等级 |
|---|---|---|---|---|
| DSH | `CA11-dsh-error` | error | pass | high |
| Codex | `CA12-codex-success` | success | pass | high |
| DSH | `CA13-dsh-success` | success | pass | high |
| Codex | `CA14-codex-error` | error | pass | high |

## 接入校准（不计入比较）

| 产品 | 运行 | 裁定 | 证据等级 |
|---|---|---|---|
| DSH | `CA00-dsh-calibration` | pass | high |
| Codex | `CA02-codex-calibration` | unknown | high |
| Codex | `CA03-codex-calibration` | pass | high |
| WorkBuddy | `WBC00-workbuddy-calibration` | unknown | high |
| WorkBuddy | `WBC01-workbuddy-calibration` | unknown | high |
| WorkBuddy | `WBC02-workbuddy-calibration` | unknown | high |

## 重复批（同题多次，测稳定性，不加题量）

| 产品 | 运行 | 题 | 裁定 | 产物分 | 证据等级 |
|---|---|---|---|---:|---|
| DSH | `dsh-sdk-T01-r2` | T01 | pass | 60 | high |
| DSH | `dsh-sdk-T01-r3` | T01 | pass | 60 | high |
| DSH | `dsh-sdk-T02-r2` | T02 | pass | 60 | high |
| DSH | `dsh-sdk-T02-r3` | T02 | pass | 60 | high |
| DSH | `dsh-sdk-T03-r2` | T03 | pass | 60 | high |
| DSH | `dsh-sdk-T03-r3` | T03 | pass | 60 | high |
| DSH | `dsh-sdk-T05-r2` | T05 | pass | 60 | high |
| DSH | `dsh-sdk-T05-r3` | T05 | pass | 60 | high |

重复批只用于回答“同一产品同一题重复跑是否稳定”，不增加题量、不改变上面的五题汇总；结果见 [CL-03](../../ledger/conclusions/CL-03.json)。

校准未走通共享工具调用，按未知保留，不记产品失败，也不进入上面的比较表。
