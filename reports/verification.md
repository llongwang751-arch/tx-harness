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

证据生命周期测试使用临时目录中的显式合成记录，只检验工具逻辑；这些记录不属于竞品实测，不导出到public。新增公开包复核器核对全部5份manifest，并独立复验两次成功预试的原生文件。Git通过.gitattributes保留原始字节，避免Windows/Linux换行转换使证据哈希失效。GitHub Actions覆盖Python3.11与公开证据，远程CI结果另记。

正式产品现场：0/75；另有Codex两attempt、WorkBuddy两次入口诊断、DSH一次真实T01预试。Codex修正后的attempt与DSH各8/8产物检查通过；没有五产品完整总分或排名。仓库：https://github.com/llongwang751-arch/tx-harness 。
