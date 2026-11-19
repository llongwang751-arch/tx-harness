# 五款 Harness 文件收发实测

2026-11-19 · 李明远

五款分别接受了一次新任务，最终回复和 `receipt.json` 原件均通过复算。**独立产品运行 5 次，有效通过 5 次，有效失败 0 次，未知 0 次。** 这些是文件收发诊断。T03-M 正式任务在本轮提交 0 次，独立抽查待回收。[机器复算结果](../../public/five-surface-20261119/results.json) · [T03-M 准入记录](codex-t03m-readiness.md)

## 题目和判定

用一份 105 字节 CSV，要求按原顺序取出 `state=settled` 的 `record`，合计整数 `amount_cents`，同时交付原生 `receipt.json` 与最终回复中的 JSON。开跑前冻结运行 ID、用例和判定。两款 CLI 从独立目录读取 CSV，三款桌面入口从附件接收。提示词正文相同，桌面粘贴省略文件末尾换行，服务端接收的文本字节未取证。各场顺序执行，每款一个新任务。[先于实跑的冻结提交](https://github.com/llongwang751-arch/tx-harness/commit/7876f914bdbee57c6b19a1d1bfa53f1190bdd77d) · [规则](../../supplements/five-surface-v1/protocol.json) · [输入](../../supplements/five-surface-v1/input.csv) · [提示词](../../supplements/five-surface-v1/prompt.txt)

两个检查分别给出通过、失败或未取得。通过要求顶层恰有 `records`（按原顺序的字符串数组）和 `total_cents`（整数），值与 CSV 复算一致。预期为 `VIOLET-74`、`TERRA-06`、`SKY-55`，合计 `1265`。缺少终态或缺少任一可核对证据时，整场记未知。未提交的入口检查、原生事件、判卷测试和两次 Codex 权限诊断均单列。

## 实际现场

时间为北京时间，记录的是提交及观察到完成的时点。桌面现场为操作记录和回复转录，CLI 和 SDK 另有去个人路径的原生事件节选。公开原件逐字节保留并登记大小及 SHA-256。证据能核对本次交付，后端模型和内置 Skill 的实际版本仍有缺口。

| 产品与使用入口 | 模型或模式证据 | 提交至观察到完成 | 最终回复 | 原始文件 | 现场与原件 |
|---|---|---|---|---|---|
| WorkBuddy 5.11.3 桌面新任务 | DeepSeek-V4.1-Flash 界面标签，默认权限 | 21:59:53–22:00:22 | 通过 | 通过 | [现场](../../public/five-surface-20261119/transfer-20261119-workbuddy-r1/observation.json) · [原件](../../public/five-surface-20261119/transfer-20261119-workbuddy-r1/receipt.json) |
| DeepSeek Harness 安装包自带 SDK | 请求 `deepseek-flash`，随包 Skill 保留 | 22:02:16–22:02:27 | 通过 | 通过 | [现场](../../public/five-surface-20261119/transfer-20261119-dsh-r1/observation.json) · [原生事件](../../public/five-surface-20261119/transfer-20261119-dsh-r1/native-events.excerpts.json) · [原件](../../public/five-surface-20261119/transfer-20261119-dsh-r1/receipt.json) |
| Codex 0.169.1 CLI | 原生 CLI 服务默认模型，具体后端未确认 | 22:05:08–22:05:40 | 通过 | 通过 | [现场](../../public/five-surface-20261119/transfer-20261119-codex-r1/observation.json) · [原生事件](../../public/five-surface-20261119/transfer-20261119-codex-r1/native-events.excerpts.json) · [原件](../../public/five-surface-20261119/transfer-20261119-codex-r1/receipt.json) |
| 腾讯元宝桌面专家模式 | 专家模式可见，具体模型未确认 | 22:07:01–22:07:52 | 通过 | 通过 | [现场](../../public/five-surface-20261119/transfer-20261119-yuanbao-r1/observation.json) · [原件](../../public/five-surface-20261119/transfer-20261119-yuanbao-r1/receipt.json) |
| 豆包桌面工作任务 → 云电脑 | 豆包 2.1 Lite（低）界面标签 | 22:12:12–22:12:59 | 通过 | 通过 | [现场](../../public/five-surface-20261119/transfer-20261119-doubao-r1/observation.json) · [原件](../../public/five-surface-20261119/transfer-20261119-doubao-r1/receipt.json) |

## 能从现场确认什么

- **五个受测入口均完成收发。** CLI/SDK 记录了实际工具调用，三个桌面入口记录了附件、最终回复和文件取回。独立于最终回复，五份原件均可用哈希核对并复算。本判断对这些样本有直接证据，各产品只有一条记录。
- **豆包的新云电脑入口能接收这份附件并导出文件。** 提交前看到了实际附件和云电脑标签，执行中显示正在读取 `input.csv`，随后从同一会话下载原件。现场支持这条新任务的链路。旧无效场仍缺会话、输入准备错误和复制链的完整证据。[旧事故记录](../week6/artifact-audit.md)
- **DSH 入口和工具表现有差异。** 开跑前桌面自动化无法稳定定位可用窗口，实际测试走自带 SDK。SDK 文件工具的写入及回读已成功，随后 Shell 的自检在 `grantWrite` 返回 Win32 5。文件交付由原件另行复算通过。之后用新工作区的只读命令复现了 Shell 启动授权错误，具体 ACL 根因仍未证实，桌面入口仍未测到。[DSH 原生事件](../../public/five-surface-20261119/transfer-20261119-dsh-r1/native-events.excerpts.json) · [独立诊断回合](dsh-shell-diagnostic-2026-11-19.md)

这轮固定了用例内容和输出契约。产品入口、权限边界、服务模型和内置 Skill 存在差异，结果只支持这些入口的端到端观察。单次通过、界面时点均不足以估计稳定性、算速度名次或拆分 Harness、模型、Skill 的贡献。Codex T03-M 的评分文件拒绝证据限于其权限诊断配置。其他入口尚无同等访问拒绝证据，正式归因继续按准入记录执行。[归因边界](../attribution-boundaries.md) · [权限记录](codex-t03m-readiness.md)

## 如何复核

完整克隆后运行以下两条命令。第一条核对冻结版本、记录时序、原件字节摘要，并分别复算回复与文件。第二条跑正确答案及字符串数值、浮点、重复键、额外字段等近似错误的回归样例。复算过程由仓库维护侧完成，独立人工抽查尚待反馈。

```text
python scripts/audit_five_surface_transfer.py --check
python -m unittest discover -s tests -p test_five_surface_transfer.py -v
```
