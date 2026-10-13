# 网页采集入口的实际阻碍

2026-10-13。本页记录采集工具状态，不是元宝或豆包的产品成绩。用户已打开并登录 Chrome；网页入口尚未提交评测任务，后续原生桌面尝试另行记录。

最初，桌面控制工具不能可靠判定 Windows 浏览器当前网址，要求结束该轮电脑操作。没有绕过该限制连接 CDP，也没有将普通聊天替代指定模式。

随后通过文档化原生电脑控制检查本应用的设置：浏览器页实际报错，缺少 `~/.codex/.tmp/bundled-marketplaces/openai-bundled/.agents/plugins/marketplace.json`；官方“重试”未恢复清单。电脑操控页没有加载出正常的 Chrome 安装按钮。工具启动所指向的 bundled Browser `browser-service.mjs` 也缺失。

只读核查发现，官方MSIX 26.1007.2314.0资源内含完整清单与浏览器服务；临时物化目录有65个staging残留。限定筛选应用启动日志发现37次copy_plugins阶段copyfile UNKNOWN错误，browser/plugin.json亦失败，未见规范目录重建成功记录。这定位到初始化复制阶段，更底层原因仍未知。CLI的marketplace add支持本地来源，但直接注册MSIX路径不能证明修复应用前置的规范目录与运行时路径；未执行此替代路线。没有手抄资源、重命名staging、修改浏览器安全策略或复制账户凭据。

实际通过原生应用“帮助→检查更新”核验，官方对话框返回“ChatGPT is up to date.”。技术包名为OpenAI.Codex，但Manifest显示名及可执行入口为ChatGPT；官方安装包Prod updater与部署文档均指向Store ID 9PLM9XGG6VKS。没有把另一个产品安装当作本机修复，也没有声称组件已重新安装成功。

用户随后确认完整退出并重新打开。新启动日志仍有4次copy_plugins UNKNOWN及4次resolve_failed，规范目录没有恢复。2026-10-13再次核对商店身份后，实际执行官方 `winget repair --id 9PLM9XGG6VKS --exact --source msstore --silent --disable-interactivity --accept-source-agreements --accept-package-agreements`；WinGet返回“修复操作成功完成”，退出码0。该命令为Repair，不是Reset。修复后包状态Ok、版本仍26.1007.2314.0，但规范marketplace及browser-service仍缺失。14:48:37 UTC在应用浏览器页再次点击官方“重试”，随后现场仍显示同一个marketplace文件不存在提示。修复命令成功不能等同于浏览器接入成功。

官方Prod Store更新源仍给出同一版本；没有取得更高版本或厂商确认的恢复步骤。本轮停止重复重启、同版本修复或重装。微软说明MSIX Repair保留数据，Reset会删除数据；本轮未执行Reset。公开问题报告与复制失败形状相似，但不能作为本机底层原因的官方确认。

另通过只读Windows应用清单发现本机已安装元宝和豆包桌面客户端，已通过文档化原生电脑控制核验各自的指定模式，并封存两款T01现场。正常原生客户端是明确登记的另一产品入口；不将其冒充网页入口，也不修改浏览器网址策略或伪装Chrome身份。网页连接仍不可用，客户端成绩另列实际版本、模式和采集边界。

官方依据：[浏览器扩展安装与排障](https://learn.chatgpt.com/docs/chrome-extension)、[Windows部署及产品身份](https://learn.chatgpt.com/docs/enterprise/windows-deployment)、[应用更新与完整退出](https://learn.chatgpt.com/docs/enterprise/manage-app-updates)。资料支持正式恢复路径，没有直接保证修复本机缺失清单。

本次修复依据：[WinGet repair](https://learn.microsoft.com/en-us/windows/package-manager/winget/repair)、[MSIX Repair与Reset](https://learn.microsoft.com/en-us/windows/msix/desktop/managing-your-msix-reset-and-repair)、[官方Store更新源](https://persistent.oaistatic.com/codex-app-prod/windows-store-update.json)。

浏览器连接恢复后仍须现场确认网页中的元宝“专家模式”和豆包“工作任务模式”、文件上传/交付与可记录边界，再冻结正式条件。当前网页入口结果为未知，不能填零分或“不支持”。原生桌面的元宝T01为7/8、42/60，豆包本地T01为产品侧失败、0/8、0/60，证据与限制见[预试索引](../public/pilots/README.md)。WorkBuddy 原生桌面入口已另行连通，不能把浏览器故障归到该产品。
