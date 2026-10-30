# T02：政策冲突裁决及证据索引

请审核 inputs/claims.csv。inputs/00_evaluation_contract.md 是本次任务明确授权的解释合同；依据它确定其它资料的权限、版本和专门例外。不要自行引入常识政策，不访问网络。金额均为整数分。

输出四份文件：

1. `decisions.csv`：列为 claim_id,decision,approved_cents,reason_code,rule_ids。每个 claim_id 一行，行序不限。decision 只能是 approved/rejected。reason_code：未减额的核准为 FULL；触及上限减额为 CAP；缺收据拒绝为 NO_RECEIPT；住宿晚数超出允许范围拒绝为 INVALID_NIGHTS。rule_ids 只填写直接决定本笔金额或拒绝理由的规则 ID，多规则时用 | 连接且按字典序；版本选择规则和解释合同不额外填写。
2. `summary.json`：顶层 claimed_cents、approved_cents、reduction_cents、approved_count、rejected_count。reduction_cents=所有申请额之和-核准额之和。
3. `evidence_index.json`：顶层 rules 数组，列出 decisions.csv 实际引用的每条规则，按 rule_id 排序，每条只含 rule_id、path、quote。path 相对于 inputs；quote 为规则正文完整一句，包含末尾标点，不包含规则 ID 标题。
4. `conflicts.json`：
   - lower_authority_rule_ids：列出与授权财务规则冲突而不能采用的 FAQ/运营规则 ID，排序；
   - scoped_override：对象，包含 winner、overridden_rule、claim_ids，说明专门例外及实际应用的申请 ID；
   - version_selection：对象，以每个 claim_id 为键，值为 finance_v2/finance_v3，专门例外适用的申请仍记录其基础财务版本。

完成条件：全部申请得到唯一裁决；不存在重复主键；金额、计数一致；引用能从指定文件逐字复核；冲突裁决严格遵循解释合同。


将交付文件写入 outputs/，不要修改 inputs/。
