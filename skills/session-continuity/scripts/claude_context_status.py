"""Render Claude Code's context usage or only its 80% handoff reminder."""

import argparse
import json
import locale
import math
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reminder-only", action="store_true")
    parser.add_argument("--lang", choices=("auto", "en", "zh"), default="auto")
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
        used = payload["context_window"]["used_percentage"]
    except (KeyError, TypeError, ValueError):
        return

    if type(used) not in (int, float) or not 0 <= used <= 100 or not math.isfinite(used):
        return
    if used < 80 and args.reminder_only:
        return
    language = args.lang
    if language == "auto":
        language = next((os.environ[key] for key in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG")
                         if os.environ.get(key)), None) or locale.getlocale()[0] or "en"
    chinese = language.lower().startswith("zh")
    status = f"上下文 {used}%" if chinese else f"Context {used}%"
    if used >= 80:
        status += " · 建议准备交接" if chinese else " · Prepare a handoff"
    print(status)


if __name__ == "__main__":
    main()
