读取 `inputs/transactions.csv`。按原始顺序列出状态恰好为 `settled` 的 ID，并对这些行的 `gross_cents - refund_cents` 求和。

把结果保存为 `outputs/summary.json`。JSON 对象应仅包含 `settled_ids`（字符串数组）和 `net_cents`（整数）。不要修改输入，不用联网。最终回复简短说明交付路径即可。
