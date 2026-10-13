# WorkBuddy T04 原生桌面预试

真实新任务；没有修复产物、额外策略提示或选择性重试。客观检查 7/7，60.0/60；额外原生产物0份全部保留。原始输入和题目未改：True。

完成观察上界116.359秒，精确服务时刻未知。模型/权限/账户可见条件见metadata；实际底模、Skill与完整工具调用不可见。E2现场只公开审阅的配置/执行标签和最终答复，思考、账号和私有历史不公开。

一个探索性episode，正式样本0；manual、总分、纯Harness分null。T04的release文件及补发前产物（如有）单列，不用incident声明替代实际现场。

复核：`python -X utf8 -m harness_eval verify --case T04 --outputs public/pilots/workbuddy-T04-desktop-r1/outputs`。manifest覆盖原字节证据；哈希不单独证明来源真实性。

公开摘录由操作人/代理审阅，未声称经过外部人工审计；按 `received_at` 稳定排序，源行号只对应私有 AX 文件。历史采集/导出源码中如有 “human-reviewed” 或“人工审阅”措辞，仅为当时的说明文本，不能当作外部人工审计证据；历史源码及其哈希保留原字节。metadata 中记录本次说明纠正前的哈希。

`inputs/rates.json` 是补发后的末态文件；初始材料只有题目和 `inputs/trades.csv`。复现缺失输入阶段时须暂扣 rates.json，再按 release.json 的 active 请求/可用时点补发同一原件；补发前 outputs 为空快照，恢复消息仍在原任务。
