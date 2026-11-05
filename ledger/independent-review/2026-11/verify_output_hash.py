"""计算 ledger reproduce 输出的规范化 SHA256（复核用，防 CRLF 平台差异）。

用法：
    python -X utf8 ledger/independent-review/2026-11/verify_output_hash.py <输出文件>

规范化 = UTF-8 读入 -> 解析 JSON -> ensure_ascii=False, indent=2, sort_keys=True
         重新序列化 + 尾部一个 LF -> UTF-8 编码 -> SHA256。
与 scripts/ledger.py --check 内部使用的规范化一致。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

EXPECTED = {
    "CL-01": "3c9eeb8ee45f13a540c70df3f29872d9ccda3ee9c8622199e9082181f302c40a",
    "CL-02": "1271c39624a0fa5f1273f304e18d69b7161b28d2ab9bb446795666b472505613",
}


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    raw = Path(argv[1]).read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"FAIL 输出不是合法 JSON: {exc}")
        return 1
    canonical = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
                 + "\n").encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    claim = value.get("claim") if isinstance(value, dict) else None
    expected = EXPECTED.get(str(claim))
    print(f"文件: {argv[1]}")
    print(f"claim: {claim}")
    print(f"规范化 SHA256: {digest}")
    if expected:
        print(f"预期 SHA256:  {expected}")
        print(f"比对结果:     {'一致' if digest == expected else '不一致——请原样记录，不要修改仓库'}")
        return 0 if digest == expected else 1
    print("比对结果:     该输出没有对应的预期哈希（请检查是否为 reproduce CL-01/CL-02 的输出）")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
