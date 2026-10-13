# 公开证据与转换说明

这是一次真实 SDK T04 多轮接入预试，不进入正式 75 次实验分母。

初始 inputs/ 仅含 trades.csv，rates.json 单列在 releases/。提示词是实际 UTF-8 提交文本，附统一交付目录约定。原生最终 outputs/、初始 trades 和实际补发 rates 均逐字节复制，文件 SHA-256 与私有执行元数据相符。初始 incident 被产品后续更新；其初始写入内容与补发前输出清单 hash 保留在真实事件及 release.json 中，没有把重建文本冒充原生快照文件。

SDK 全量 wire 包含隐藏系统上下文和 reasoning，保留在 gitignored 的 private/pilots/dsh-T04-r1；未公开 raw stdout。公开投射只取该父 session 的 committed assistant/message 的 text 块、真实 tool/call、append tool/result、turn/step 状态。其余内容（包括 reasoning、assistant attempts/streams、system/runtime context、非所选 session 的记录）均不公开。一个诊断 Skill 正文被省略，只留调用、完成状态及原始正文 hash；用户主目录（含 Windows 8.3 短名）统一为 C:/Users/<user>；参与者绝对工作区路径替换为 <participant_workspace>，临时 Skill 资源路径替换为 <product_skill_temp>。公开控制帧和文本因此是经过声明转换的投射，不再逐字节等于私有原始帧。

公开 SDK lifecycle 文件另取该父 session 的 running/idle 通知与四个协议收据，只保留所需字段。

保留的公开事件和发往 SDK 的四个控制帧已由操作人逐项敏感信息审查，没有凭据值。每个公开事件标明原始 stdout 行号与接收时间；接收时间不是服务端发生时间。私有源文件 hash 用于关联来源，不能独立证明现场真实性。

首次用户任务 20:49:57.835（北京时间），40.345 秒时收到明确请求，58.397 秒补发 fixture 并发送统一恢复消息。观察员语义复核耗时 18.052 秒，因此不称即时补发，也不用该次预试推断正式产品速度。两轮使用一个 session 和一个原生 SDK runtime；初始化、两次 durable enqueue receipt、两次 completed turn/end、第二轮 idle 和 shutdown 都有原生记录，没有强制杀死首轮。

助手关于“无假设”“未联网”“完全正确”等文字属于产品主张。公开工具事件支持缺失文件的查验、主动请求、实际补发后读取、文件写入及错误事实；独立确定性检查支持最终产物的 7/7 正确性。尚不能把计算正确单独归给模型、Skill 或 Harness，也不能把 Windows ACL 错误推广到全部 DSH 环境。
