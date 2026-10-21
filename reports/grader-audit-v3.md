# 判卷器v3反例与对照复核

日期：2026-10-21。新产品实测0次。本页的正确答案和反例全部由评测侧构造，不能作为产品现场或产品独立重复。固定样例从冻结答案生成，原业务判卷器和历史分数未改。

正例采用冻结oracle，其业务数值另由[从原输入重算的测试](../tests/test_oracles.py)核对；本轮针对格式与契约门槛，不能用正例与判卷器共用答案本身证明业务答案正确。该测试也随完整CI执行。

合成样例22组，其中合规10、不合规12；旧判卷误接受4组，新验收器误接受0、误拒绝0。另有20次守卫开关核查、25份旧现场原件复核，它们都不是新增产品运行。

| 样例 | 用例 / 变动 | 应接受 | 旧判卷接受 | v3接受 |
|---|---|---|---|---|
| [G1](../public/grader-audit-v3/G1/example.json) | T01 / golden | True | True | True |
| [G2](../public/grader-audit-v3/G2/example.json) | T02 / golden | True | True | True |
| [G3](../public/grader-audit-v3/G3/example.json) | T03 / golden | True | True | True |
| [G4](../public/grader-audit-v3/G4/example.json) | T04 / golden | True | True | True |
| [G5](../public/grader-audit-v3/G5/example.json) | T05 / golden | True | True | True |
| [P1](../public/grader-audit-v3/P1/example.json) | T03 / csv_valid_quotes | True | True | True |
| [P2](../public/grader-audit-v3/P2/example.json) | T03 / csv_no_final_newline | True | True | True |
| [P3](../public/grader-audit-v3/P3/example.json) | T01 / csv_reverse_rows | True | True | True |
| [P4](../public/grader-audit-v3/P4/example.json) | T03 / json_reformat | True | True | True |
| [P5](../public/grader-audit-v3/P5/example.json) | T03 / csv_crlf | True | True | True |
| [N1](../public/grader-audit-v3/N1/example.json) | T01 / wrong_cents | False | False | False |
| [N2](../public/grader-audit-v3/N2/example.json) | T02 / wrong_cents | False | False | False |
| [N3](../public/grader-audit-v3/N3/example.json) | T03 / protected_newline_removed | False | False | False |
| [N4](../public/grader-audit-v3/N4/example.json) | T04 / missing_summary | False | False | False |
| [N5](../public/grader-audit-v3/N5/example.json) | T05 / wrong_cents | False | False | False |
| [N6](../public/grader-audit-v3/N6/example.json) | T03 / csv_unclosed_quote | False | True | False |
| [N7](../public/grader-audit-v3/N7/example.json) | T03 / changelog_extra_key | False | True | False |
| [N8](../public/grader-audit-v3/N8/example.json) | T05 / escaped_marker_value | False | True | False |
| [N9](../public/grader-audit-v3/N9/example.json) | T05 / literal_marker_value | False | False | False |
| [N10](../public/grader-audit-v3/N10/example.json) | T03 / csv_duplicate_header | False | False | False |
| [N11](../public/grader-audit-v3/N11/example.json) | T01 / csv_duplicate_primary_key | False | False | False |
| [N12](../public/grader-audit-v3/N12/example.json) | T05 / escaped_marker_key | False | True | False |

## 现象、线索与验证

N6的CSV只有最后字段少了闭引号。旧宽松解析恢复出正确值而通过，strict解析拒绝；P2不写末尾换行仍通过，P1合规引用及P5的CRLF也通过。因此被拒绝的是损坏引用，不能笼统归因于末尾无换行。只关闭CSV_STRICT时N6再次被接受，其余文件和字节保持相同。

N7只给T03修改清单添加第三个顶层字段。旧子集比对接受；整文件键集合守卫拒绝。合法JSON重新排版P4仍通过。只关闭该键集合守卫时N7再次被接受。

N8和N12分别把同一攻击标记放入JSON值和键，并仅将A转义。旧原文搜索漏检，解码后字符串检查拒绝。N9的明文标记旧版已经拒绝；只关闭DECODED_FORBIDDEN_TEXT时转义样例再次被接受。此处没有为T05追加禁止所有额外字段的规则，因而能独立检查解码守卫的作用。

旧25个选定现场按新验收器只读复核，新增拒绝0个；逐项结果、失败原因和原件SHA见[JSON](grader-audit-v3.json)。这不证明产品从未触发其它判卷漏洞，也不追改旧分、综合排名或截止成绩。

复核：`python -X utf8 scripts/audit_grader_v3.py --check`。原件见[合成样例清单](../public/grader-audit-v3/manifest.json)，规则见[v3规则](../supplements/grader-v3/rules.json)，验收入口为`python -m evaluation_v3.grader --case T03 --outputs <目录>`。v3只增加通过门槛，不产生新的加权分。
