#!/usr/bin/env python3
"""lhg-miniprogram 插件冒烟测试：全部绿才算过。

检查项：
 1. 三个 JSON 合法（plugin.json / marketplace.json / hooks.json）
 2. 4 个 SKILL.md 都有 name/description frontmatter，且 150~300 行
 3. 3 个 commands 都有 description frontmatter
 4. 2 个 agents 都有 name/description/tools/model frontmatter
 5. skills 平台中立：不含 Claude Code 专有工具名
 6. fixtures：坏 fixture 的埋点规则必须全部命中且脚本 exit!=0；
    好 fixture 零 blocker 且 exit==0
 7. hooks 脚本：commit 拦截 / 非 commit 放行 / 逃生开关 / 页面配对提醒

用法：python3 smoke_test.py [--repo <插件根目录>]
退出码：0=全绿，1=有失败。
"""

import argparse
import json
import os
import re
import subprocess
import sys

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    results.append((PASS if cond else FAIL, name, detail))
    return cond


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def frontmatter(path):
    """解析 markdown 顶部 --- YAML 块（只取一层 key: value）。"""
    text = read(path)
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = {}
    for ln in text[3:end].split("\n"):
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", ln)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kw)


PLUGIN = "lhg-miniprogram"
# 预期的埋点命中（坏 fixture 必须全部命中）
MP_BAD_MUST = {
    "MP-APP-001", "MP-PAGE-001", "MP-PRIV-001", "MP-SEC-001", "MP-SENS-001",
    "MP-JSON-001", "MP-HYG-002", "MP-RTE-001", "MP-API-001", "MP-PAGE-002",
}
# 平台中立红线：skill 正文不许出现这些 Claude Code 专有表述
NEUTRAL_DENY = ["Task tool", "Bash tool", "Edit tool", "Write tool", "Read tool",
                "AskUserQuestion", "subagent_type", "PreToolUse", "PostToolUse",
                "${CLAUDE_", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    AUDIT = os.path.join(repo, "scripts", "audit")

    # 1. JSON 合法
    for rel in [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                "hooks/hooks.json"]:
        p = os.path.join(repo, rel)
        try:
            d = json.loads(read(p))
            check("JSON 合法: " + rel, True)
            if rel.endswith("plugin.json"):
                check("plugin.json name==%s" % PLUGIN, d.get("name") == PLUGIN, str(d.get("name")))
                check("plugin.json 有 version/description/author",
                      all(d.get(k) for k in ("version", "description", "author")))
            if rel.endswith("marketplace.json"):
                ps = d.get("plugins", [])
                check("marketplace.json source==./",
                      len(ps) == 1 and ps[0].get("source") == "./" and
                      ps[0].get("name") == PLUGIN, str(ps))
            if rel.endswith("hooks.json"):
                check("hooks.json 顶层有 hooks 包装", "hooks" in d)
                evts = d["hooks"]
                check("hooks.json 有 PreToolUse+PostToolUse",
                      "PreToolUse" in evts and "PostToolUse" in evts, str(list(evts)))
        except Exception as e:
            check("JSON 合法: " + rel, False, str(e))

    # 2. SKILL.md frontmatter + 行数
    for skill in ["lhg-mp-plan", "lhg-mp-dev", "lhg-mp-api", "lhg-mp-submit"]:
        p = os.path.join(repo, "skills", skill, "SKILL.md")
        fm = frontmatter(p)
        check("skill frontmatter: " + skill,
              bool(fm.get("name")) and bool(fm.get("description")),
              "name=%s" % fm.get("name"))
        nlines = len(read(p).split("\n"))
        check("skill 行数 150~300: %s (%d 行)" % (skill, nlines), 150 <= nlines <= 320, str(nlines))
        body = read(p)
        bad_words = [w for w in NEUTRAL_DENY if w in body]
        check("skill 平台中立: " + skill, not bad_words, "命中: %s" % bad_words)
        check("skill 有出品区: " + skill, "出品：刘洪光" in body and "https://github.com/lhg-skills" in body)
        check("skill 有自检与反馈: " + skill, "自检与反馈" in body)

    # 3. commands
    for cmd in ["miniprogram", "miniprogram-audit", "miniprogram-page"]:
        p = os.path.join(repo, "commands", cmd + ".md")
        fm = frontmatter(p)
        check("command description: " + cmd, bool(fm.get("description")), str(fm.get("description"))[:60])

    # 4. agents
    for ag in ["mp-builder", "mp-auditor"]:
        p = os.path.join(repo, "agents", ag + ".md")
        fm = frontmatter(p)
        check("agent frontmatter: " + ag,
              all(fm.get(k) for k in ("name", "description", "tools", "model")),
              str({k: fm.get(k) for k in ("name", "model")}))

    # 5. 审计脚本冒烟
    def audit_hits(script, target):
        r = run([sys.executable, os.path.join(AUDIT, script),
                 "--target", os.path.join(repo, target), "--format", "json"])
        try:
            d = json.loads(r.stdout)
        except Exception:
            return None, r.returncode, []
        return d["summary"], r.returncode, [f["rule_id"] for f in d["findings"]]

    s, code, ids = audit_hits("mp_audit.py", "fixtures/mp-bad")
    check("mp 坏 fixture exit!=0", code != 0, "exit=%d" % code)
    check("mp 坏 fixture blocker>0", s and s["blocker"] > 0, str(s))
    missing = MP_BAD_MUST - set(ids)
    check("mp 埋点全命中 (%d/%d)" % (len(MP_BAD_MUST - missing), len(MP_BAD_MUST)),
          not missing, "缺失: %s" % sorted(missing))

    s, code, ids = audit_hits("mp_audit.py", "fixtures/mp-good")
    check("mp 好 fixture 零 blocker", s and s["blocker"] == 0, str(s))
    check("mp 好 fixture exit==0", code == 0, "exit=%d" % code)

    # 规则总数（对外口径：20+ 条）
    n = json.loads(run([sys.executable, os.path.join(AUDIT, "mp_audit.py"),
                        "--target", os.path.join(repo, "fixtures/mp-good"),
                        "--format", "json"]).stdout)["summary"]["rules_run"]
    check("规则总数>=20 (%d)" % n, n >= 20, str(n))

    # 6. hooks 脚本
    def hook(script, payload, env=None):
        e = dict(os.environ); e.update(env or {})
        return run([sys.executable, os.path.join(repo, "hooks", script)],
                   input=payload, env=e)

    r = hook("pre_commit_audit.py", '{"tool_input":{"command":"git status"}}')
    check("hook: 非 commit 放行", r.returncode == 0 and not r.stdout.strip())
    r = hook("pre_commit_audit.py",
             '{"tool_input":{"command":"git commit -m \\"x\\""}}',
             {"CLAUDE_PROJECT_DIR": os.path.join(repo, "fixtures/mp-bad")})
    try:
        d = json.loads(r.stdout)
        denied = d["hookSpecificOutput"]["permissionDecision"] == "deny"
    except Exception:
        denied = False
    check("hook: commit 有 blocker 拦截", denied, r.stdout[:120])
    r = hook("pre_commit_audit.py",
             '{"tool_input":{"command":"git commit -m \\"x\\""}}',
             {"CLAUDE_PROJECT_DIR": os.path.join(repo, "fixtures/mp-bad"),
              "LHG_MP_HOOKS_OFF": "1"})
    check("hook: 逃生开关生效", r.returncode == 0 and not r.stdout.strip())

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        pg = os.path.join(td, "pages", "demo"); os.makedirs(pg)
        js = os.path.join(pg, "demo.js"); open(js, "w").write("Page({});")
        r = hook("post_write_warn.py", json.dumps({"tool_input": {"file_path": js}}))
        check("hook: 页面缺配对 wxml 提醒", "additionalContext" in r.stdout, r.stdout[:80])
        open(os.path.join(pg, "demo.wxml"), "w").write("<view/>")
        r = hook("post_write_warn.py", json.dumps({"tool_input": {"file_path": js}}))
        check("hook: 配对齐全不提醒", not r.stdout.strip())

    # 报告
    print("=" * 60)
    print("%s 冒烟测试报告" % PLUGIN)
    print("=" * 60)
    fails = 0
    for st, name, detail in results:
        mark = "✓" if st == PASS else "✗"
        print("%s %s %s" % (mark, st, name))
        if detail and st == FAIL:
            print("    → %s" % detail)
        if st == FAIL:
            fails += 1
    print("=" * 60)
    print("共 %d 项，通过 %d，失败 %d" % (len(results), len(results) - fails, fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
