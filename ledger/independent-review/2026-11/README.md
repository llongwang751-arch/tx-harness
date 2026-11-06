# 独立复核操作单：CL-01 / CL-02（2026-11 批次）

本包让**任何人**都能在不读本仓库实现代码的情况下复跑两条结论命令并机械比对规范化哈希。回应 Issue #1 第 3 问（"谁可以独立复核 CL-01/02，能否在不看实现与预期结论的情况下运行命令并记录差异"）——答案是：任何人，按本单四步即可。

## 本机已完成的自证记录（2026-11-06/07，作者环境）

本项目为单人评测，以下是作者本人实际执行并留档的验证；它不是人员独立的第三方复核，如实声明：

| 验证 | 内容 | 结果 |
|---|---|---|
| 双跑确定性 | `reproduce CL-01/CL-02` 各连跑两次，stdout 逐字节一致 | 一致 |
| 规范化哈希 | 两次输出的规范化 SHA256 与结论 JSON 登记值比对 | CL-01 `3c9eeb8e…` 一致；CL-02 `1271c396…` 一致 |
| 干净克隆自包含 | `git clone` 到全新目录（无 `private/`、无 `runs/`），重跑两条命令与 `--check` | 哈希一致；14 项检查全过 |
| 提交后复验 | 每次推送后从最新提交重新克隆复跑 | 一致（2026-11-07，commit 98941a3） |

## 复核步骤（任何人可执行）

1. 克隆仓库并记录 commit：

   ```bash
   git clone https://github.com/llongwang751-arch/tx-harness.git
   cd tx-harness
   git rev-parse HEAD        # 记录到记录表
   ```

2. 运行两条只读复现命令，把完整输出各存为一个文件：

   ```bash
   python -X utf8 scripts/ledger.py reproduce CL-01 > cl01-output.txt
   python -X utf8 scripts/ledger.py reproduce CL-02 > cl02-output.txt
   ```

3. 计算规范化哈希并与预期比对：

   ```bash
   python -X utf8 ledger/independent-review/2026-11/verify_output_hash.py cl01-output.txt
   python -X utf8 ledger/independent-review/2026-11/verify_output_hash.py cl02-output.txt
   ```

4. 运行仓库自带审计（预期 14 项检查全过）：

   ```bash
   python -X utf8 scripts/ledger.py --check
   ```

5. 把命令记录、环境、哈希与发现填入 [review-form.md](review-form.md) 留档。

## 环境

- Python ≥ 3.11（无任何第三方依赖）；任意操作系统。
- Windows 用户注意：**不要直接对终端输出计算 SHA256**——Windows 管道是 CRLF 行尾，直接算会永远不匹配。用本包的 [verify_output_hash.py](verify_output_hash.py) 计算规范化哈希。

## 预期规范化哈希

| 结论 | expected_output_sha256 |
|---|---|
| CL-01 | `3c9eeb8ee45f13a540c70df3f29872d9ccda3ee9c8622199e9082181f302c40a` |
| CL-02 | `1271c39624a0fa5f1273f304e18d69b7161b28d2ab9bb446795666b472505613` |

## 规范化说明（verify_output_hash.py 做的事）

输出是 `json.dumps(..., ensure_ascii=False, indent=2, sort_keys=True) + "\n"` 的 UTF-8 字节。
规范化 = 按 UTF-8 读入 → 解析为 JSON → 以相同参数重新序列化 → 追加一个 `\n` → 编码 UTF-8（LF 行尾）→ SHA256。
这一步消除 CRLF/尾随空白等平台差异；`scripts/ledger.py --check` 内部用的正是同一规范化。

## 复核的边界（如实记录，不要放大）

- 能证明：在复核环境中，两条命令可以运行、输出与冻结哈希一致（或记录不一致）；
- 不能证明：历史采集现场真实、哈希覆盖之外的行为正确、以及"人员独立"——单人项目的本机自证不等于第三方复核；
- 输出不一致**不是复核失败**，而是重要发现：请原样记录你的输出与哈希，不要尝试改仓库去凑哈希。

## 归档

填好的 review-form.md 与输出文件放在本目录（`2026-11/`），文件名用复核日期前缀；如哈希不一致，另开一条 ledger unknowns 记录，不得静默刷新 expected_output_sha256。
