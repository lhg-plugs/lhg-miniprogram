#!/usr/bin/env python3
"""lhg-miniprogram 硬门②（警告级，不拦截）：写页面文件时缺配对文件则提醒。

触发：PostToolUse / Write|Edit。只做提醒，永远 exit 0、不拦截写入。
小程序一个页面通常是 .js + .wxml 配对（.wxss/.json 按需）；
只写了其中一半，另一半大概率是忘了。

逃生方式：LHG_MP_HOOKS_OFF=1（环境变量）可关闭本提醒；
或 /plugin disable lhg-miniprogram 停用整个插件。
零第三方依赖。
"""

import json
import os
import sys

# 页面必需的配对关系：写了 key 却没有 value → 提醒
PAIR_RULES = {
    ".js": (".wxml", "页面逻辑(.js)已写，但同目录下没有配对的 .wxml 结构文件"),
    ".wxml": (".js", "页面结构(.wxml)已写，但同目录下没有配对的 .js 逻辑文件"),
}
PAGE_EXTS = {".js", ".wxml", ".wxss", ".json"}


def main() -> int:
    if os.environ.get("LHG_MP_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""
    if not file_path:
        return 0

    stem, ext = os.path.splitext(file_path)
    if ext not in PAIR_RULES:
        return 0
    # 只关心 pages/ 或 components/ 下的文件，避免误伤 utils 等
    norm = file_path.replace("\\", "/")
    if "/pages/" not in norm and "/components/" not in norm:
        return 0

    need_ext, reason = PAIR_RULES[ext]
    sibling = stem + need_ext
    if os.path.isfile(sibling):
        return 0

    msg = (
        "页面配对提醒（lhg-miniprogram）：%s\n"
        "建议补上 %s；如确为分步编写可忽略。\n"
        "关闭本提醒：export LHG_MP_HOOKS_OFF=1（当前会话有效）。"
    ) % (reason, sibling)
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
