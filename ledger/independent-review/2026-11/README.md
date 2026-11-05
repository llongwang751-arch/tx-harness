# 独立复核操作单：CL-01 / CL-02（2026-11 批次）

状态：**待同事执行**。本包由作者准备（2026-11-07），回应 Issue #1 第 2 条要求："请一位未参与实现的同事复跑 CL-01、CL-02，并将实际命令、环境、输出哈希、发现和签署记录归档。AI 辅助检查不能替代这个独立复核。"

## 复核人要求

- 未参与本仓库判卷/台账代码的实现；
- 复核时**先只看本操作单**，运行命令并记录原始输出，再看预期哈希做机械比对；
- 全程不需要访问 private/ 目录，不需要启动任何产品。

## 环境

- Python ≥ 3.11（无任何第三方依赖）；
- 任意操作系统；Windows 用户注意：**不要直接对终端输出计算 SHA256**——Windows 管道是 CRLF 行尾，直接算会永远不匹配。用本包的 [verify_output_hash.py](verify_output_hash.py) 计算规范化哈希，或手工按"规范化说明"处理。

## 步骤

1. 克隆仓库并记录 commit：

   ```bash
   git clone https://github.com/llongwang751-arch/tx-harness.git
   cd tx-harness
   git rev-parse HEAD        # 记录到签署表
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

5. 把命令记录、环境、哈希、发现填入 [review-form.md](review-form.md) 并签名。

## 预期规范化哈希

| 结论 | expected_output_sha256 |
|---|---|
| CL-01 | `3c9eeb8ee45f13a540c70df3f29872d9ccda3ee9c8622199e9082181f302c40a` |
| CL-02 | `1271c39624a0fa5f1273f304e18d69b7161b28d2ab9bb446795666b472505613` |

## 规范化说明（verify_output_hash.py 做的事）

输出是 `json.dumps(..., ensure_ascii=False, indent=2, sort_keys=True) + "\n"` 的 UTF-8 字节。
规范化 = 按 UTF-8 读入 → 解析为 JSON → 以相同参数重新序列化 → 追加一个 `\n` → 编码 UTF-8（LF 行尾）→ SHA256。
这一步消除 CRLF/尾随空白等平台差异；`scripts/ledger.py --check` 内部用的正是同一规范化。

## 复核的边界（复核人请如实记录，不要放大）

- 能证明：在复核人的独立环境中，两条命令可以运行、输出与冻结哈希一致（或记录不一致）；
- 不能证明：历史采集现场真实、哈希覆盖之外的行为正确；
- 输出不一致**不是复核失败**，而是重要发现：请原样记录你的输出与哈希，不要尝试改仓库去凑哈希。

## 归档

签署后的 review-form.md 与两个输出文件放在本目录（`2026-11/`），文件名用复核日期前缀；如哈希不一致，另开一条 ledger unknowns 记录，不得静默刷新 expected_output_sha256。
