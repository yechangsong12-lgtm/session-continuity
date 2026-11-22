"""Render Claude Code's context usage or only its 80% handoff reminder."""

import argparse
import json
import math
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reminder-only", action="store_true")
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
        used = payload["context_window"]["used_percentage"]
    except (KeyError, TypeError, ValueError):
        return

    if type(used) not in (int, float) or not 0 <= used <= 100 or not math.isfinite(used):
        return
    if used >= 80:
        print(f"上下文 {used}% · 建议准备交接")
    elif not args.reminder_only:
        print(f"上下文 {used}%")


if __name__ == "__main__":
    main()
