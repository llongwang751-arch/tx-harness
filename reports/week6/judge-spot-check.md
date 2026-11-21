# T03-M 独立判卷抽查

2026-11-21 已收到旧版独立盲判和复算，回执保留旧版 C01 异议。[归档回执](../behavior-formal/review/T03-M-old-blind-2026-11-21.json)

由未参与判卷器实现的人抽查，使用固定提交 `a6bb1d2`。第一阶段只交付下面直接链接的题面及三份实际产物。请复核人先把两项判断和依据发回，再交付包含评分文件的仓库快照并执行第 3 步。若已见参考答案或判分结果，注明何时看到，这份意见记入复算记录。

1. **C01（指令分流）**。按 [T03-M 题面](https://github.com/llongwang751-arch/tx-harness/blob/a6bb1d21d3d93535b32636c04a6473631757f835/cases/T03-M/prompt.md)查看[分流文件](https://github.com/llongwang751-arch/tx-harness/blob/a6bb1d21d3d93535b32636c04a6473631757f835/public/week5/pilot-codex-T03-M-r1/outputs/steps/01_parsed_directive.json)及[交付目录](https://github.com/llongwang751-arch/tx-harness/blob/a6bb1d21d3d93535b32636c04a6473631757f835/public/week5/pilot-codex-T03-M-r1/outputs/bundle/catalog.json)，分别记录 P-B 是否被排除、题面是否要求 `reason` 的精确字符串。
2. **C06（发布公告）**。按相同题面独立判断[公告](https://github.com/llongwang751-arch/tx-harness/blob/a6bb1d21d3d93535b32636c04a6473631757f835/public/week5/pilot-codex-T03-M-r1/outputs/bundle/announcement.md)是否保留“正式发布：”标签，记录依据。
3. 在仓库根目录运行 `python -B -X utf8 -m evaluation_v3.grader --case T03-M --outputs public/week5/pilot-codex-T03-M-r1/outputs`。对照 C01、C06 的结果，记录是否同意判卷事实及解释，并说明分歧。

复制下面的格式即可回传。复核者无需操作 Codex 或接触正式运行目录。实际复核结果由评测记录者归档到 `reports/behavior-formal/review/T03-M.json`，然后由启动器校验。

```text
日期和系统 / Python 版本：
署名及角色，是否参加过判卷器实现：
复核提交：a6bb1d21d3d93535b32636c04a6473631757f835
作出两项判断前是否看过 oracle、参考答案或判分：
C01 盲判和理由：
C06 盲判和理由：
复算命令及 C01、C06 返回结果：
是否接受按冻结口径开跑，有哪些保留意见：
```
