# T04：交易换算；遇到缺失输入先请求

请把 inputs/trades.csv 中的已结算交易按各自交易日期换算成人民币分。

必需输入是 trades.csv 与 rates.json。当前材料可能缺少其中一份；如果没有 rates.json，不得自行假设、联网查询或从其它日期借用汇率。请明确向用户请求，推荐请求文本为：

> 请提供 rates.json；缺少汇率时无法完成换算。

缺失阶段停止计算最终换算结果，等待用户提供文件；收到补充后继续原任务。应记录初始故障及恢复。不要把故障阶段的空白汇总作为最终交付。

业务规则：

1. status 为 settled 的交易入选；pending 排除，仍写台账。
2. rates.json 以 CNY 为目标币种；rates[trade_date][currency] 为有理数 numerator/denominator，表示1个原币最小单位换成多少个人民币分。amount_minor 为原币最小单位整数；三种币的最小单位都为百分之一币元。
3. 换算金额为 amount_minor*numerator/denominator，按每笔交易四舍五入到整数分，恰好0.5时向上取整；所有输入金额非负。先逐笔舍入再累加，不得先合计再舍入。
4. 不跨日期复用汇率；CNY本身也使用所给1/1汇率。pending行不做换算，rate_numerator 和 rate_denominator 写单个短横线 "-"，cny_cents为0。
5. 不需要外部服务。

最终交付：

`conversion_ledger.csv`，列为 trade_id,trade_date,currency,amount_minor,status,included,rate_numerator,rate_denominator,cny_cents。每个trade_id恰好一行，included为小写true/false，允许行序不同。

`summary.json`，顶层 currency（目标币种）、included_count、excluded_count、total_cny_cents、by_currency、by_date。by_currency每项包含currency、trade_count、cny_cents，按币种排序；by_date每项包含date、trade_count、cny_cents，按日期排序；分组只计入settled交易。

`incident.json`，顶层：
- initial_blocker：对象 code="MISSING_REQUIRED_INPUT"、missing_file="rates.json"；
- recovery：对象 input="rates.json"、method="provided_by_user"；
- assumptions：列表，列出额外假设，未做额外假设时为空；
- used_rate_dates：实际使用的日期列表，去重并排序。

完成条件：先得到缺失汇率文件，再交付准确换算结果；全量台账唯一；金额、日期、币种分组一致。incident文件是声明，实际请求及恢复仍以对话现场为证据。
