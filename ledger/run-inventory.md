# 运行逐条清单（47 条）

由 `scripts/verify_run_inventory.py` 从 `ledger/runs.jsonl` 与 git 历史重建；
`--check` 可复核本表与台账、与入账提交三方一致。窗口归属按运行**发生日期**计，
与按**入账提交日期**计的台账增长（10-31 当天 39→41→45→47）分开陈述，见周报。

| run_id | 发生日期 | 轨道 | 产品 | 任务 | 判定 | 入账提交 | 窗口归属 |
|---|---|---|---|---|---|---|---|
| codex-T01-r1-attempt02 | 2026-10-13 | 五题端到端 | Codex | T01 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| codex-T02-r1-attempt01 | 2026-10-13 | 五题端到端 | Codex | T02 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| codex-T03-r1-attempt01 | 2026-10-13 | 五题端到端 | Codex | T03 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| codex-T04-r1-attempt02 | 2026-10-13 | 五题端到端 | Codex | T04 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| codex-T05-r1-attempt01 | 2026-10-13 | 五题端到端 | Codex | T05 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| doubao-T01-desktop-r2 | 2026-10-13 | 五题端到端 | 豆包工作任务模式 | T01 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| doubao-T02-desktop-r1 | 2026-10-13 | 五题端到端 | 豆包工作任务模式 | T02 | pass 60.0/60 | 0e658db | 历史材料入账（窗口前） |
| doubao-T03-desktop-r1 | 2026-10-13 | 五题端到端 | 豆包工作任务模式 | T03 | pass 60.0/60 | 0e658db | 历史材料入账（窗口前） |
| doubao-T04-desktop-r1 | 2026-10-13 | 五题端到端 | 豆包工作任务模式 | T04 | pass 60.0/60 | 0e658db | 历史材料入账（窗口前） |
| doubao-T05-desktop-r1 | 2026-10-13 | 五题端到端 | 豆包工作任务模式 | T05 | pass 60.0/60 | 0e658db | 历史材料入账（窗口前） |
| dsh-T04-r1 | 2026-10-13 | 五题端到端 | DSH | T04 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| dsh-sdk-T01-r1 | 2026-10-13 | 五题端到端 | DSH | T01 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| dsh-sdk-T02-r1 | 2026-10-13 | 五题端到端 | DSH | T02 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| dsh-sdk-T03-r1 | 2026-10-13 | 五题端到端 | DSH | T03 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| dsh-sdk-T05-r1 | 2026-10-13 | 五题端到端 | DSH | T05 | fail 30/60 | 0e658db | 历史材料入账（窗口前） |
| workbuddy-T01-desktop-r1 | 2026-10-13 | 五题端到端 | WorkBuddy | T01 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| workbuddy-T02-desktop-r1 | 2026-10-13 | 五题端到端 | WorkBuddy | T02 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| workbuddy-T03-desktop-r1 | 2026-10-13 | 五题端到端 | WorkBuddy | T03 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| workbuddy-T04-desktop-r1 | 2026-10-13 | 五题端到端 | WorkBuddy | T04 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| workbuddy-T05-desktop-r1 | 2026-10-13 | 五题端到端 | WorkBuddy | T05 | pass 60/60 | 0e658db | 历史材料入账（窗口前） |
| yuanbao-T01-desktop-r1 | 2026-10-13 | 五题端到端 | 元宝专家模式 | T01 | fail 42/60 | 0e658db | 历史材料入账（窗口前） |
| yuanbao-T02-desktop-r1 | 2026-10-13 | 五题端到端 | 元宝专家模式 | T02 | fail 27/60 | 0e658db | 历史材料入账（窗口前） |
| yuanbao-T03-desktop-r1 | 2026-10-13 | 五题端到端 | 元宝专家模式 | T03 | fail 0/60 | 0e658db | 历史材料入账（窗口前） |
| yuanbao-T04-desktop-r1 | 2026-10-13 | 五题端到端 | 元宝专家模式 | T04 | pass 60.0/60 | 0e658db | 历史材料入账（窗口前） |
| yuanbao-T05-desktop-r1 | 2026-10-13 | 五题端到端 | 元宝专家模式 | T05 | fail 30.0/60 | 0e658db | 历史材料入账（窗口前） |
| R01-reopen | 2026-10-21 | 原生桌面 | WorkBuddy | S02 | pass | 0e658db | 历史材料入账（窗口前） |
| R02-control | 2026-10-21 | 原生桌面 | WorkBuddy | S02 | pass | 0e658db | 历史材料入账（窗口前） |
| W01-control | 2026-10-21 | 原生桌面 | WorkBuddy | S02 | pass | 0e658db | 历史材料入账（窗口前） |
| W02-window-reopen | 2026-10-21 | 原生桌面 | WorkBuddy | S02 | unknown | 0e658db | 历史材料入账（窗口前） |
| CA00-dsh-calibration | 2026-10-23 | 接入校准 | DSH | S01 | pass | 0e658db | 历史材料入账（窗口前） |
| CA02-codex-calibration | 2026-10-23 | 接入校准 | Codex | S01 | unknown | 0e658db | 历史材料入账（窗口前） |
| CA03-codex-calibration | 2026-10-23 | 接入校准 | Codex | S01 | pass | 0e658db | 历史材料入账（窗口前） |
| CA11-dsh-error | 2026-10-23 | 固定响应主臂 | DSH | S01 | pass | 0e658db | 历史材料入账（窗口前） |
| CA12-codex-success | 2026-10-23 | 固定响应主臂 | Codex | S01 | pass | 0e658db | 历史材料入账（窗口前） |
| CA13-dsh-success | 2026-10-23 | 固定响应主臂 | DSH | S01 | pass | 0e658db | 历史材料入账（窗口前） |
| CA14-codex-error | 2026-10-23 | 固定响应主臂 | Codex | S01 | pass | 0e658db | 历史材料入账（窗口前） |
| WBC00-workbuddy-calibration | 2026-10-23 | 接入校准 | WorkBuddy | S01 | unknown | 0e658db | 历史材料入账（窗口前） |
| WBC01-workbuddy-calibration | 2026-10-23 | 接入校准 | WorkBuddy | S01 | unknown | 0e658db | 历史材料入账（窗口前） |
| WBC02-workbuddy-calibration | 2026-10-23 | 接入校准 | WorkBuddy | S01 | unknown | 0e658db | 历史材料入账（窗口前） |
| dsh-sdk-T01-r2 | 2026-10-30 | 同题重复 | DSH | T01 | pass 60.0/60 | 18fadd3 | 第3周新增（10-25至10-31） |
| dsh-sdk-T01-r3 | 2026-10-30 | 同题重复 | DSH | T01 | pass 60.0/60 | 18fadd3 | 第3周新增（10-25至10-31） |
| dsh-sdk-T02-r2 | 2026-10-30 | 同题重复 | DSH | T02 | pass 60.0/60 | b5e8f7b | 第3周新增（10-25至10-31） |
| dsh-sdk-T02-r3 | 2026-10-30 | 同题重复 | DSH | T02 | pass 60.0/60 | b5e8f7b | 第3周新增（10-25至10-31） |
| dsh-sdk-T03-r2 | 2026-10-30 | 同题重复 | DSH | T03 | pass 60.0/60 | a3c88b0 | 第3周新增（10-25至10-31） |
| dsh-sdk-T03-r3 | 2026-10-30 | 同题重复 | DSH | T03 | pass 60.0/60 | a3c88b0 | 第3周新增（10-25至10-31） |
| dsh-sdk-T05-r2 | 2026-10-30 | 同题重复 | DSH | T05 | pass 60.0/60 | a3c88b0 | 第3周新增（10-25至10-31） |
| dsh-sdk-T05-r3 | 2026-10-30 | 同题重复 | DSH | T05 | pass 60.0/60 | a3c88b0 | 第3周新增（10-25至10-31） |

合计 47 条；按窗口：历史材料入账（窗口前）=39；第3周新增（10-25至10-31）=8。
