# 独立复核签署表（CL-01 / CL-02，2026-11 批次）

> 复核人填写。填完连同两个输出文件一起归档在本目录。未能完成的项写"未完成+原因"，不要留空。

## 一、复核人与环境

| 项 | 值 |
|---|---|
| 姓名/署名 | |
| 与本项目的关系（确认未参与实现） | |
| 复核日期 | |
| 操作系统 | |
| Python 版本（`python -V`） | |
| 仓库 commit（`git rev-parse HEAD`） | |
| 克隆来源 | |

## 二、命令记录

按[操作单](README.md)逐步执行，把每条命令的实际返回码与关键输出片段贴在下表（输出文件另存归档）。

| 命令 | 返回码 | 备注（耗时、异常等） |
|---|---|---|
| `git clone …` | | |
| `python -X utf8 scripts/ledger.py reproduce CL-01 > cl01-output.txt` | | |
| `python -X utf8 scripts/ledger.py reproduce CL-02 > cl02-output.txt` | | |
| `python -X utf8 ledger/independent-review/2026-11/verify_output_hash.py cl01-output.txt` | | |
| `python -X utf8 ledger/independent-review/2026-11/verify_output_hash.py cl02-output.txt` | | |
| `python -X utf8 scripts/ledger.py --check` | | 预期 14 项检查全过 |

## 三、哈希比对

| 结论 | 你的规范化哈希 | 预期哈希 | 是否一致 |
|---|---|---|---|
| CL-01 | | `3c9eeb8e…2c40a`（完整值见操作单） | |
| CL-02 | | `1271c396…5613`（完整值见操作单） | |

## 四、发现

（不一致、异常、看不懂的输出都写在这里；"无发现"也要写明"复核通过，无差异"。）

## 五、签署

- 复核人签名：＿＿＿＿＿＿＿＿ 日期：＿＿＿＿＿＿
- 作者收到归档的确认（由作者补填）：日期 ＿＿＿＿，处理方式：＿＿＿＿（一致→在本周报引用；不一致→开 ledger unknowns 记录并回应）
