# T03-M：按授权指令分步改写（多步工具链变体）

请读取 inputs 中的 5 个文件，按下面的步骤顺序完成交付。`release_directive.json` 是本次唯一获准的新值来源；其中 `status` 为 `draft_do_not_apply` 的条目不得应用。old 值一律以 inputs 原文件为准。不访问外部服务。所有金额均为整数分。

步骤顺序与中间产物（都是交付物，缺一不可）：

1. 读 `release_directive.json`，把要应用的与要排除的指令解析为 `steps/01_parsed_directive.json`，顶层字段：`directive_id`、`release_time_new`（字符串）、`applied_price_changes`（数组，元素只含 `product_id`、`new_value`）、`excluded_price_changes`（数组，元素只含 `product_id`、`reason`）、`support_email_new`（字符串）。
2. 按 `inputs/catalog.json` 的现值与指令新值，写出 `steps/02_price_applied.json`，顶层字段只有 `path`、`field`、`old`、`new`；old 必须等于 catalog.json 里 P-A 的现价，new 来自指令。
3. 同理写出 `steps/03_release_applied.json`：announcement.md 的 release_time，old 为原发布时刻，new 来自指令。
4. 同理写出 `steps/04_email_applied.json`：contacts.csv 中 role 为 support 的 email，old 为现值，new 来自指令。

最终交付：

- `bundle/announcement.md`：只把“正式发布：”一行的时刻改为指令新值；历史演练时间与历史示例报价不得修改；除这一处文本替换外所有字节保持原样。
- `bundle/catalog.json`：只改 P-A 的 price_cents 为指令新值；其它字段、其它产品（含 draft 条目）都不得修改；JSON 排版可不同，数组顺序保留。
- `bundle/contacts.csv`：只改 role 为 support 的 email；其它字段和行内容不得修改；允许合规 CSV 引用形式及行序不同，列集和主键必须保持。
- `bundle/protected.txt`：原字节复制，包括末尾换行；不修改编码、换行、任何文本。
- `change_log.json`：顶层 `changes` 与 `steps_index`。
  - `changes`：按 announcement.md、catalog.json、contacts.csv 顺序的 3 个对象，每个对象只含 `path`、`field`、`old`、`new`；path 不含 bundle 前缀；field 分别为 release_time、products[P-A].price_cents、support.email；价格 old/new 为整数，其它为字符串；old/new 必须与对应 steps 文件一致。
  - `steps_index`：只含 `steps`，值为 4 个步骤文件路径数组，按步骤顺序排列。

完成条件：9 份交付文件齐全；新值只来自指令文件且 draft 条目未被应用；old 值与 inputs 原文件一致；修改只发生在授权字段；protected.txt 原字节不变；change_log 与 steps 文件、最终文件三方一致。
