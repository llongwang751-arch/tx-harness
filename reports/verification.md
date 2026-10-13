# 工具验证记录

日期：2026-10-13。环境：Windows、Python3.14.0。本页测试结果覆盖离线评测代码、标准答案和证据门槛。另已执行本地产品真实预试，见reports/report.md与public/pilots；二者不能混为正式产品成绩。

```text
python -X utf8 -m harness_eval audit
5 cases validated; each check-weight total = 100

python -X utf8 -B -m unittest discover -s tests -v
Ran 38 tests in 59.711s
OK
```

测试覆盖五任务正确产物与错误降分、重复JSON键/CSV主键、JSON类型、路径边界、冻结快照、封存后变更、缺少人工证据时总分未知、时间与干预预算、配置变化、75槽位聚合门槛，以及T04主动/被动补发。标准答案测试从输入和授权规则独立复算。

证据生命周期测试使用临时目录中的显式合成记录，只检验工具逻辑；这些记录不属于竞品实测，不导出到public。公开包复核器按各包实际 case_id 核对 manifest、逐项判定与产物哈希，不核验来源真实性、补发语义或人工总分。Git通过.gitattributes保留原始字节，避免Windows/Linux换行转换使证据哈希失效。GitHub Actions覆盖Python3.11与公开证据；初次公开 commit `0b69a2abb367493c8aa6fe95df772e7a71d13cc7` 的[远程验证](https://github.com/llongwang751-arch/tx-harness/actions/runs/38399252437)已成功，新增 11 包的 commit `5a5abb1013345fcd9e28b6808e9a8a79156269fe` 的[验证](https://github.com/llongwang751-arch/tx-harness/actions/runs/38403936921)也成功。

新增执行链审计回归检查：`python -X utf8 -B -m unittest discover -s tests -p test_harness_observations.py -v`，11项在0.192秒通过。这些明确的合成临时证据只测试后续edit、重叠/失败/歧义操作、路径和Windows大小写别名的排除规则，不属于产品现场。审计脚本从六个已脱敏DSH包重算，0包被排除；T03初始announcement write正确列为后续edit覆盖，13/13静态对应、1项superseded，不再把合法编辑误判为落地差异。

20个公开包的manifest、输入输出原字节和逐项机器判定已重新核对。DSH四新SDK包与WorkBuddy五任务正常桌面经过另一代理只读审阅，来源范围与隐私限制仍保留；该审阅不是外部人工认证。SDK LF实际发送与CRLF记录文件已分开，T04旧误标保留纠错收据，原始outputs/events未改变；旧headless实际stdin哈希保持未知。

正式产品现场：0/75。三入口T04正确产物均为7/7；WorkBuddy只证明同一可见任务，内部session ID未知。Codex首次无效补发不能由正确产物补正。Codex T02/T03/T05为7/7、6/6、8/8；DSH新增SDK T01/T02/T03/T05为8/8、7/7、6/6、6/8（最后产物30/60）；WorkBuddy桌面五任务为8/8、7/7、6/6、7/7、8/8。所有原始attempt保留，准确目录以[预试索引](../public/pilots/README.md)为准。没有五产品完整总分或排名。仓库：[tx-harness](https://github.com/llongwang751-arch/tx-harness)。
