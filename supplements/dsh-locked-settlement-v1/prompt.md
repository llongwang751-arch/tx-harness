# 商户结算对账

读取 `inputs/orders.csv`、`inputs/vendors.csv`、`inputs/policy.json`。按订单原始行序处理。每笔排除的订单只记录第一个适用的原因，优先级以 policy 文件的 `rejection_priority` 为准。

- `unsupported_currency`：订单币种不是 policy 的 `currency`。
- `not_settled`：订单状态不是 `settled`。
- `unknown_vendor`：订单商户不在商户表。
- `vendor_paused`：对应商户的状态不是 `active`。
- `invalid_refund`：退款小于 0 或超过订单总额。

正常订单逐笔计算。计费基数为总额扣减退款，手续费为基数乘商户费率（基点），折算到分后按四舍五入取整数，结算金额为基数扣手续费。所有金额单位为分。

提交三份文件：

1. `outputs/ledger.csv`，表头依次是 `order_id,vendor_id,gross_cents,refund_cents,fee_cents,payable_cents`，按原订单顺序列出正常订单。
2. `outputs/rejects.csv`，表头依次是 `order_id,reason`，按原订单顺序列出排除订单。
3. `outputs/summary.json`，顶层只有四个整数键 `eligible_count`、`rejected_count`、`total_fee_cents`、`total_payable_cents`。金额只统计正常订单。

只访问本次提供的输入，保留其字节。将输出写入指定目录，不使用联网查询。最终回复注明三个交付文件路径。
