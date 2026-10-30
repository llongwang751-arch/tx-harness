# T01：订单与退款去重统计

请根据 inputs/orders.csv 和 inputs/refunds.csv 生成三个文件。金额单位均为分，不使用小数元。不要访问网络。

## 业务规则

1. 两张表分别按“业务 ID + revision”识别完全相同的重复行，重复副本只计一次；`exact_duplicate_*_rows` 统计被删除的副本数量。数据不含同一 ID 同一 revision 内容不一致的情况。
2. 去掉完全重复副本后，同一业务 ID 只保留 revision 最大的记录；`superseded_*_rows` 统计被最新版替代的旧记录数量。
3. 只将订单最新状态为 paid 或 shipped 的订单计入总体和客户组汇总。cancelled 与 pending 不计入。
4. 退款也先去重和选最新版。仅 status=success 且关联入选订单的退款影响统计。退款可能存在多个独立退款 ID，需要累加。
5. 孤儿退款：最新退款引用的 order_id 在最新订单集合中不存在。非成功退款、不合格订单退款与孤儿退款分别报告。提供的数据中这三类不重叠。
6. 每个最新订单都要写入台账。排除订单仍保留其原始 gross_cents，但 successful_refund_cents 与 net_cents 为 0。入选订单 net_cents=gross_cents-successful_refund_cents。included 写小写 true/false。

## 交付文件和格式

`order_ledger.csv`：列必须为
`order_id,customer_group,status,gross_cents,successful_refund_cents,net_cents,included`。
每个 order_id 恰好一行，允许行序不同。

`aggregate.json`：
- total：order_count、gross_cents、refund_cents、net_cents；
- groups：每个客户组一个对象，包含 customer_group、order_count、gross_cents、refund_cents、net_cents。按 customer_group 升序排列，仅输出有入选订单的组。

`exceptions.json`：顶层字段为
exact_duplicate_order_rows、superseded_order_rows、exact_duplicate_refund_rows、superseded_refund_rows、
orphan_refund_ids、ignored_non_success_refund_ids、ignored_ineligible_order_refund_ids。
计数用整数，所有 ID 数组按字典序排列。

完成条件：三份文件可解析；台账无重复主键；汇总和异常严格按上述规则计算。不要把输入材料中的旧版本当作额外业务记录。


将交付文件写入 outputs/，不要修改 inputs/。
