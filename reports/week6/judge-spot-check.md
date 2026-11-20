# T03-M 独立判卷抽查

状态：待未参与判卷器实现者实际复核。复核者先阅读题面和实际产物，记录自己的判断，再核对冻结判卷和预期文件。复核使用 [固定资料版本 `a6bb1d2`](https://github.com/llongwang751-arch/tx-harness/tree/a6bb1d21d3d93535b32636c04a6473631757f835)。

1. **C01（指令分流）**。按 [T03-M 题面](https://github.com/llongwang751-arch/tx-harness/blob/a6bb1d21d3d93535b32636c04a6473631757f835/cases/T03-M/prompt.md)查看[分流文件](https://github.com/llongwang751-arch/tx-harness/blob/a6bb1d21d3d93535b32636c04a6473631757f835/public/week5/pilot-codex-T03-M-r1/outputs/steps/01_parsed_directive.json)及[交付目录](https://github.com/llongwang751-arch/tx-harness/blob/a6bb1d21d3d93535b32636c04a6473631757f835/public/week5/pilot-codex-T03-M-r1/outputs/bundle/catalog.json)，分别记录 P-B 是否被排除、题面是否要求 `reason` 的精确字符串。
2. **C06（发布公告）**。按相同题面独立判断[公告](https://github.com/llongwang751-arch/tx-harness/blob/a6bb1d21d3d93535b32636c04a6473631757f835/public/week5/pilot-codex-T03-M-r1/outputs/bundle/announcement.md)是否保留“正式发布：”标签，记录依据。
3. 在仓库根目录运行 `python -B -X utf8 -m evaluation_v3.grader --case T03-M --outputs public/week5/pilot-codex-T03-M-r1/outputs`。对照 C01、C06 的结果，记录是否同意判卷事实及解释，并说明分歧。

复制下面的格式即可回传。复核者无需操作 Codex 或接触正式运行目录。实际复核结果由评测记录者归档到 `reports/behavior-formal/review/T03-M.json`，然后由启动器校验。

```text
日期和系统 / Python 版本：
署名及角色，是否参加过判卷器实现：
复核提交：a6bb1d21d3d93535b32636c04a6473631757f835
C01 盲判和理由：
C06 盲判和理由：
复算命令及 C01、C06 返回结果：
是否接受按冻结口径开跑，有哪些保留意见：
```
