# 新批次的产物有效性验收

入口从仓库根目录运行：

```powershell
python -X utf8 -m evaluation_v3.grader --case T03 --outputs public/grader-audit-v3/N6/outputs
```

该反例的旧判卷结果仍是60/60，但新版`accepted`为false。后续新产物须同时满足冻结业务检查和新版有效性守卫；不要只取`legacy_artifact_result.objective_score`当作新版验收结论。命令输出判定JSON，正常退出仅表示生成结果，验收状态以`accepted`字段为准。

新增规则见[规则版本](../supplements/grader-v3/rules.json)：严格解析CSV，核对T03修改清单的整文件键集合，并检查JSON解码后的禁词。没有创建新的100分权重，`new_weighted_score`为null。既有`harness_eval`入口用于复算历史分数，保留其原实现；历史分不改写。

API中的`disabled_rules`只供公开的守卫开关诊断，结果同时记录被关闭的规则，不能作为全规则开启的正式验收。新产品实验若使用v3，应在开始前将规则、代码SHA和计分/无效处理方式纳入新协议，不把本次合成诊断追认为产品预注册试验。

本版只覆盖[固定反例和合法对照](../reports/grader-audit-v3.md)及25份公开旧原件的影响复核，未证明一般判卷正确性，也不重建截止快照。
