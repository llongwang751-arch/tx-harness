# T03-M 独立判卷抽查

状态：待未参与实现者实际复核。复核者先阅读题面和实际产物，记录自己的判断，再核对冻结判卷和预期文件。

1. 按 [T03-M 题面](../../cases/T03-M/prompt.md)独立判断[公告](../../public/week5/pilot-codex-T03-M-r1/outputs/bundle/announcement.md)是否保留“正式发布：”标签，记录依据。
2. 查看[分流文件](../../public/week5/pilot-codex-T03-M-r1/outputs/steps/01_parsed_directive.json)，分别记录 P-B 是否被正确排除，以及题面是否要求 `reason` 的精确字符串。
3. 在仓库根目录运行 `python -B -X utf8 -m evaluation_v3.grader --case T03-M --outputs public/week5/pilot-codex-T03-M-r1/outputs`。对照 C01、C06 的结果，记录是否同意判卷事实及解释，并说明分歧。

请记录日期、Git 提交、命令、环境、两项判断及理由。将实际结果另存归档，不改本操作单。
