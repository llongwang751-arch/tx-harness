# 网页采集入口的实际阻碍

2026-10-13。本页记录采集工具状态，不是元宝或豆包的产品成绩。用户已打开并登录 Chrome；尚未向两款指定模式提交评测任务。

最初，桌面控制工具不能可靠判定 Windows 浏览器当前网址，要求结束该轮电脑操作。没有绕过该限制连接 CDP，也没有将普通聊天替代指定模式。

随后通过文档化原生电脑控制检查本应用的设置：浏览器页实际报错，缺少 `~/.codex/.tmp/bundled-marketplaces/openai-bundled/.agents/plugins/marketplace.json`；官方“重试”未恢复清单。电脑操控页没有加载出正常的 Chrome 安装按钮。工具启动所指向的 bundled Browser `browser-service.mjs` 也缺失。

只读核查发现，官方MSIX 26.1007.2314.0资源内含完整清单与浏览器服务；临时物化目录有65个staging残留。限定筛选应用启动日志发现37次copy_plugins阶段copyfile UNKNOWN错误，browser/plugin.json亦失败，未见规范目录重建成功记录。这定位到初始化复制阶段，更底层原因仍未知。CLI的marketplace add支持本地来源，但直接注册MSIX路径不能证明修复应用前置的规范目录与运行时路径；未执行此替代路线。没有手抄资源、重命名staging、修改浏览器安全策略或复制账户凭据。

实际通过原生应用“帮助→检查更新”核验，官方对话框返回“ChatGPT is up to date.”。技术包名为OpenAI.Codex，但Manifest显示名及可执行入口为ChatGPT；官方安装包Prod updater与部署文档均指向Store ID 9PLM9XGG6VKS。没有把另一个产品安装当作本机修复，也没有声称组件已重新安装成功。

下一步是完整退出当前桌面应用后重新打开，再试设置中的 Browser/Computer Use 安装。完整退出可能重新触发初始化，这是结合本机资源与官方重启建议的修复尝试，尚未验证成功。若失败，再通过官方更新或 Microsoft Store 安装途径恢复应用。仅关闭窗口可能保留后台进程；退出并重开当前承载采集连接的应用需要用户配合，先保存所有进行中的证据。

官方依据：[浏览器扩展安装与排障](https://learn.chatgpt.com/docs/chrome-extension)、[Windows部署及产品身份](https://learn.chatgpt.com/docs/enterprise/windows-deployment)、[应用更新与完整退出](https://learn.chatgpt.com/docs/enterprise/manage-app-updates)。资料支持正式恢复路径，没有直接保证修复本机缺失清单。

浏览器连接恢复后仍须现场确认元宝“专家模式”和豆包“工作任务模式”、文件上传/交付与可记录边界，再冻结正式条件。当前两款结果为未知，不能填零分或“不支持”。WorkBuddy 原生桌面入口已另行连通，不能把浏览器故障归到该产品。
