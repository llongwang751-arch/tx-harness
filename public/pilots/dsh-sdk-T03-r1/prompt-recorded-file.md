# T03：多文件定点改写

请读取 inputs 中的4个文件，并把修改后的副本交付到 outputs 中的 bundle 目录；不要求原地修改输入。

唯一获准的修改：

1. announcement.md 的“正式发布：”那一行，时间从 `2026-10-20 10:00` 改为 `2026-10-22 14:30`。同文件里的历史演练时间和历史示例报价不得修改。该公告除这一处文本替换之外，所有字节保持原样。
2. catalog.json 的 products 数组中，id 为 P-A 的 price_cents 从119900改为129900。其它字段值、其它产品都不得修改；JSON排版可不同，数组顺序保留。
3. contacts.csv 中 role 为 support 的 email 从 support@example.test 改为 help@example.test。其它字段和行内容均不得修改；允许合规CSV引用形式及行序不同，列集和主键必须保持。
4. protected.txt 原字节复制到 bundle/protected.txt，包括末尾换行；不修改编码、换行、任何文本。

不得添加其它业务修改，不访问外部服务。所有金额均为整数分；文件内同样的数值不代表同一可修改字段。

交付文件：
- bundle/announcement.md
- bundle/catalog.json
- bundle/contacts.csv
- bundle/protected.txt
- change_log.json

change_log.json 含两个顶层字段：
- changes：按 announcement.md、catalog.json、contacts.csv 的顺序排列的3个对象，每个对象只含 path、field、old、new。path 不含 bundle 前缀。field 分别为 release_time、products[P-A].price_cents、support.email。价格 old/new 为整数，其它为字符串。
- unchanged_paths：值为 ["protected.txt"]。

完成条件：4份文件齐全；修改只发生在授权字段；protected.txt原字节不变；修改清单与实际文件一致。


将交付文件写入 outputs/，不要修改 inputs/。
