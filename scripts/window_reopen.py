"""Byte and receipt checks for the registered window-reopen study.

This is an artifact checker, not a desktop driver or a claim of remote state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def judge(probe: bytes, outputs: Path):
    results = {}
    for name in ("stage-a.txt", "stage-b.txt", "receipt.json"):
        path = outputs / name
        results[name] = {"obtained": path.is_file()}
        if path.is_file():
            data = path.read_bytes()
            results[name].update(bytes=len(data), sha256=sha(data))
            if name.endswith(".txt"):
                results[name]["matches_input"] = data == probe
    receipt = results["receipt.json"]
    if receipt["obtained"]:
        expected = {"stage": "B", "source": "probe.txt", "bytes": len(probe), "sha256": sha(probe)}
        try:
            def unique_keys(pairs):
                obj = {}
                for key, value in pairs:
                    if key in obj:
                        raise ValueError("duplicate JSON key")
                    obj[key] = value
                return obj
            actual = json.loads((outputs / "receipt.json").read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
            receipt["contract_valid"] = (actual == expected and type(actual.get("bytes")) is int)
        except (ValueError, UnicodeError):
            receipt["contract_valid"] = False
    complete = all(results[n].get("matches_input", False) for n in ("stage-a.txt", "stage-b.txt")) and receipt.get("contract_valid", False)
    return {"rule_version": "window-reopen/v1", "files": results, "joint_delivery_pass": complete,
            "limits": "Only obtained bytes are checked. Timing, UI delivery, task identity and intervention need separate scene evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(judge(args.probe.read_bytes(), args.outputs), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
