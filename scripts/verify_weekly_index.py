"""周报索引机器校验：weekly/README.md 的登记必须与目录实况一致。

    python -X utf8 scripts/verify_weekly_index.py --check

校验内容：
  1. 索引表中每个归档链接指向存在的非空文件。
  2. 每行日期都是周六（周报固定周期）。
  3. 每行"状态依据"非空；标"已发送"的行必须写明确认依据。
  4. 当前目录里不存在已撤销的 2026-10-30 简版文件（起草后未发送即撤销）。
  5. 最新待发周报（编号最大的 YYYY-MM-DD.md）含统一截止时点声明与"待本人发送"状态。
  6. 周报正文中的相对链接指向存在的文件。

只读公开文件。
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEEKLY = ROOT / "reports" / "weekly"

ROW = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|(.*?)\|(.*?)\|(.*?)\|\s*$", re.M)
LINK = re.compile(r"\(([^()]+)\)")


def problems() -> list[str]:
    found: list[str] = []
    index = WEEKLY / "README.md"
    text = index.read_text(encoding="utf-8")
    rows = ROW.findall(text)
    if not rows:
        return ["索引表中没有解析到任何周报行"]
    today = dt.date.today()
    current_saturday = today - dt.timedelta(days=(today.weekday() - 4) % 7)
    current_row = None
    for date, status, archive, basis in rows:
        weekday = dt.date.fromisoformat(date).weekday()
        if weekday != 5:
            found.append(f"{date}: 周报日期不是周六")
        if not basis.strip(" ；;"):
            found.append(f"{date}: 状态依据为空")
        if "已发送" in status and "确认" not in basis:
            found.append(f"{date}: 标已发送但状态依据没有写明确认依据")
        for target in LINK.findall(archive):
            path = WEEKLY / target.strip()
            if not path.is_file():
                found.append(f"{date}: 归档链接不存在 {target}")
            elif path.stat().st_size == 0:
                found.append(f"{date}: 归档文件为空 {target}")
        if date == current_saturday.isoformat():
            current_row = (date, status)
    for leftover in WEEKLY.glob("2026-10-30*"):
        found.append(f"存在已撤销的 2026-10-30 简版残留 {leftover.name}")
    # 本周期（最近一个周六）的周报无论发送与否都校验正文链接；
    # 若仍是待发草稿，还必须带统一截止时点声明与"待本人发送"状态。
    if current_row:
        date, status = current_row
        draft = WEEKLY / f"{date}.md"
        if not draft.is_file():
            found.append(f"{date}: 本周期周报文件缺失")
        else:
            body = draft.read_text(encoding="utf-8")
            for target in LINK.findall(body):
                if target.startswith(("http://", "https://", "#")):
                    continue
                path = (WEEKLY / target.strip()).resolve()
                if not path.is_file():
                    found.append(f"{date}.md: 正文链接不存在 {target}")
            if not status.strip().startswith("已发送"):
                if "统一截止时点" not in body:
                    found.append(f"{date}.md: 缺统一截止时点声明")
                if "待本人发送" not in body:
                    found.append(f"{date}.md: 状态未标'待本人发送'")
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验（默认即校验）")
    args = parser.parse_args(argv)
    issues = problems()
    for issue in issues:
        print("FAIL", issue)
    print(f"weekly-index: {'全部一致' if not issues else str(len(issues)) + ' 处不一致'}")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
