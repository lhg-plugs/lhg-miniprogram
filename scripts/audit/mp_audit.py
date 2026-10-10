#!/usr/bin/env python3
"""lhg-miniprogram 确定性提审审计：21 条规则，零第三方依赖。

扫描目标目录的小程序工程（app.json / project.config.json / pages / components），
输出 JSON 与人类可读报告；有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。

用法：
    python3 mp_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则文案均为本项目原创（思路受微信小程序公开文档的合规要求启发，
未复制任何第三方原文；审核规则以微信官方最新文档为准）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-miniprogram/mp-audit"

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", "fixtures",
    "miniprogram_npm", ".vscode",
}
SCAN_EXTS = {".js", ".wxml", ".wxss", ".json"}
SENSITIVE_WORDS = ["赌博", "博彩", "六合彩", "色情", "三级片", "法轮", "台独"]
PRIVACY_APIS = ["getPhoneNumber", "getUserProfile", "getUserInfo", "chooseLocation",
                "getLocation", "chooseAddress", "getWeRunData"]


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line", "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line, snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


def collect_files(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext in SCAN_EXTS:
                out.append(os.path.join(root, f))
    return sorted(out)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity,
             "category": category, "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


def _mk(rule_id, path, line, snippet):
    r = _RULE_BY_ID[rule_id]
    return Finding(r["id"], r["severity"], r["category"], r["title"],
                   path, line, snippet[:160], r["detail"])


def _line_hits(rule_id, lines, path, pattern, flags=0):
    rx = re.compile(pattern, flags)
    return [_mk(rule_id, path, i + 1, ln.strip())
            for i, ln in enumerate(lines) if rx.search(ln)]


def _load_json(path):
    try:
        return json.loads(read_text(path)), None
    except Exception as e:
        return None, str(e)


# ---------------- 工程配置 ----------------

@rule("MP-APP-001", "blocker", "工程配置", "缺 project.config.json",
      "项目根目录没有 project.config.json，微信开发者工具无法识别为小程序工程。请用开发者工具新建项目或补上该文件。")
def r_app_001(lines, text, path, ctx):
    if ctx.get("_app001_done"):
        return []
    ctx["_app001_done"] = True
    if not os.path.isfile(os.path.join(ctx["target"], "project.config.json")):
        return [_mk("MP-APP-001", "(项目)", 1, "(项目根目录)")]
    return []


@rule("MP-APP-002", "blocker", "工程配置", "appid 未配置",
      "project.config.json 里没有 appid 或为空。提审必须绑定正式 AppID，先在公众平台申请。")
def r_app_002(lines, text, path, ctx):
    if ctx.get("_app002_done"):
        return []
    ctx["_app002_done"] = True
    cfg_path = os.path.join(ctx["target"], "project.config.json")
    if not os.path.isfile(cfg_path):
        return []
    cfg, _ = _load_json(cfg_path)
    appid = (cfg or {}).get("appid", "")
    if not appid:
        return [_mk("MP-APP-002", "project.config.json", 1, "(appid 为空)")]
    ctx["appid"] = appid
    return []


@rule("MP-APP-003", "warning", "工程配置", "appid 疑似测试号",
      "appid 为 touristappid（开发者工具测试号）。体验版/提审前必须换成公众平台申请的正式 AppID。")
def r_app_003(lines, text, path, ctx):
    if ctx.get("_app003_done"):
        return []
    ctx["_app003_done"] = True
    if ctx.get("appid") == "touristappid":
        return [_mk("MP-APP-003", "project.config.json", 1, '"appid": "touristappid"')]
    return []


@rule("MP-APP-004", "blocker", "工程配置", "app.json 非法 JSON",
      "app.json 解析失败，小程序无法启动。检查括号、逗号与引号（app.json 不支持注释）。")
def r_app_004(lines, text, path, ctx):
    if ctx.get("_app004_done"):
        return []
    ctx["_app004_done"] = True
    app_path = os.path.join(ctx["target"], "app.json")
    if not os.path.isfile(app_path):
        return [_mk("MP-APP-004", "(项目)", 1, "(缺 app.json)")]
    cfg, err = _load_json(app_path)
    if cfg is None:
        return [_mk("MP-APP-004", "app.json", 1, "JSON 解析失败: %s" % err)]
    ctx["app_json"] = cfg
    return []


@rule("MP-APP-005", "blocker", "工程配置", "app.json 缺 pages",
      "app.json 的 pages 为空或缺失，小程序没有可启动的页面。至少注册一个页面路径。")
def r_app_005(lines, text, path, ctx):
    if ctx.get("_app005_done"):
        return []
    ctx["_app005_done"] = True
    pages = (ctx.get("app_json") or {}).get("pages") or []
    if not pages:
        return [_mk("MP-APP-005", "app.json", 1, "(pages 为空)")]
    ctx["pages"] = pages
    return []


# ---------------- 页面路由 ----------------

@rule("MP-PAGE-001", "blocker", "页面路由", "注册的页面缺文件",
      "app.json pages 里声明的页面缺少 .js 或 .wxml 文件，运行时会白屏/报错。补齐文件或从 pages 中移除。")
def r_page_001(lines, text, path, ctx):
    if ctx.get("_page001_done"):
        return []
    ctx["_page001_done"] = True
    out = []
    for p in ctx.get("pages") or []:
        base = os.path.join(ctx["target"], p)
        for ext in (".js", ".wxml"):
            if not os.path.isfile(base + ext):
                out.append(_mk("MP-PAGE-001", "app.json", 1, "%s 缺 %s" % (p, ext)))
    return out


@rule("MP-PAGE-002", "warning", "页面路由", "页面文件未注册",
      "pages/ 下有完整的页面文件（.js+.wxml），但未在 app.json pages 注册，用户进不去。确认是否遗漏注册。")
def r_page_002(lines, text, path, ctx):
    if ctx.get("_page002_done"):
        return []
    ctx["_page002_done"] = True
    pages = set(ctx.get("pages") or [])
    out = []
    pages_dir = os.path.join(ctx["target"], "pages")
    if not os.path.isdir(pages_dir):
        return []
    for root, _, files in os.walk(pages_dir):
        stems = {os.path.splitext(f)[0] for f in files}
        exts = {os.path.splitext(f)[1] for f in files}
        if ".js" in exts and ".wxml" in exts:
            for stem in stems:
                if ".js" in {os.path.splitext(f)[1] for f in files if f.startswith(stem)} \
                   and ".wxml" in {os.path.splitext(f)[1] for f in files if f.startswith(stem)}:
                    rel = os.path.relpath(os.path.join(root, stem), ctx["target"]).replace(os.sep, "/")
                    if rel not in pages:
                        out.append(_mk("MP-PAGE-002", rel + ".js", 1, "(未在 app.json pages 注册)"))
    return out


@rule("MP-JSON-001", "blocker", "页面路由", "页面/组件 json 非法",
      "某个 .json 解析失败（页面配置/组件配置），对应页面会加载异常。检查括号与逗号。")
def r_json_001(lines, text, path, ctx):
    if not path.endswith(".json"):
        return []
    if os.path.basename(path) in ("app.json", "project.config.json", "sitemap.json"):
        return []
    _, err = _load_json(path)
    if err:
        return [_mk("MP-JSON-001", path, 1, "JSON 解析失败: %s" % err)]
    return []


@rule("MP-RTE-001", "warning", "页面路由", "tabBar 页面用了 navigateTo",
      "tabBar 页面只能用 wx.switchTab 跳转，用 wx.navigateTo 会失败。请改 switchTab。")
def r_rte_001(lines, text, path, ctx):
    if not path.endswith(".js"):
        return []
    tab_pages = set()
    for item in (ctx.get("app_json") or {}).get("tabBar", {}).get("list", []):
        pp = (item.get("pagePath") or "").lstrip("/")
        if pp:
            tab_pages.add(pp)
    if not tab_pages:
        return []
    out = []
    for i, ln in enumerate(lines):
        if "wx.navigateTo" in ln:
            for tp in tab_pages:
                if tp in ln or ("/" + tp) in ln:
                    out.append(_mk("MP-RTE-001", path, i + 1, ln.strip()))
    return out


# ---------------- 隐私合规 ----------------

@rule("MP-PRIV-001", "blocker", "隐私合规", "未检测到隐私协议处理",
      "项目内未见 wx.onNeedPrivacyAuthorization / wx.requirePrivacyAuthorize / "
      "wx.openPrivacyContract 任一调用，且 app.json 未声明 requirePrivacyAuthorize。"
      "涉及用户个人信息的小程序提审会被打回：先在公众平台填写《隐私保护指引》，再实现同意弹窗逻辑。")
def r_priv_001(lines, text, path, ctx):
    if ctx.get("_priv001_done"):
        return []
    ctx["_priv001_done"] = True
    if ctx.get("has_privacy_api"):
        return []
    if (ctx.get("app_json") or {}).get("requirePrivacyAuthorize"):
        return []
    return [_mk("MP-PRIV-001", "(项目)", 1, "(项目级：未检测到隐私协议处理逻辑)")]


@rule("MP-PRIV-002", "warning", "隐私合规", "调用隐私接口但未见隐私声明",
      "代码调用了 getPhoneNumber/getUserProfile/位置等隐私相关接口，但项目内未见隐私协议弹窗逻辑。"
      "确认已在公众平台填写隐私保护指引，并在调用前完成用户同意流程，否则提审可能被打回。")
def r_priv_002(lines, text, path, ctx):
    if ctx.get("_priv002_done"):
        return []
    ctx["_priv002_done"] = True
    if ctx.get("has_privacy_api"):
        return []
    hits = [api for api in PRIVACY_APIS if api in (ctx.get("all_text") or "")]
    if hits:
        return [_mk("MP-PRIV-002", "(项目)", 1, "调用了: %s" % "、".join(hits))]
    return []


# ---------------- 安全 ----------------

@rule("MP-SEC-001", "blocker", "安全", "硬编码 appsecret",
      "代码里直接写了 appsecret / session_key。appsecret 只能放在服务端，泄露会被盗用接口配额。立即移到服务端并更换密钥。")
def r_sec_001(lines, text, path, ctx):
    if not path.endswith(".js"):
        return []
    return _line_hits("MP-SEC-001", lines, path,
                      r"\b(appsecret|app_secret|session_key)\b\s*[:=]\s*[\"'][^\"']{4,}[\"']", re.I)


# ---------------- 包体积 ----------------

@rule("MP-SIZE-001", "warning", "包体积", "代码体积疑似超主包限制",
      "扫描到的代码文件总体积超过 2MB（主包限制的启发式阈值）。请用分包（subpackages）拆分，或压缩图片/清理无用文件。"
      "准确限制以微信官方最新文档为准。")
def r_size_001(lines, text, path, ctx):
    if ctx.get("_size001_done"):
        return []
    ctx["_size001_done"] = True
    total = 0
    for p in ctx.get("files") or []:
        try:
            total += os.path.getsize(p)
        except OSError:
            pass
    if total > 2 * 1024 * 1024:
        return [_mk("MP-SIZE-001", "(项目)", 1, "代码总体积约 %.1fMB" % (total / 1024 / 1024))]
    return []


# ---------------- 内容合规 ----------------

@rule("MP-SENS-001", "blocker", "内容合规", "疑似敏感词",
      "文本中出现敏感词，提审极可能被打回。请人工复核上下文，确认无违规内容。")
def r_sens_001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        for w in SENSITIVE_WORDS:
            if w in ln:
                out.append(_mk("MP-SENS-001", path, i + 1, "命中敏感词: %s" % w))
                break
    return out


@rule("MP-PAY-001", "warning", "内容合规", "疑似虚拟商品支付按钮",
      "页面出现购买/支付/充值字样。注意：iOS 端小程序内不许提供虚拟商品购买（会员/课程/道具等），"
      "否则可能被封禁支付接口。请人工确认该支付是否合规，必要时在 iOS 端隐藏。")
def r_pay_001(lines, text, path, ctx):
    if not path.endswith(".wxml"):
        return []
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"<button[^>]*>", ln) and re.search(r"购买|支付|充值|开通会员|付费", ln):
            out.append(_mk("MP-PAY-001", path, i + 1, ln.strip()))
    return out


# ---------------- 数据与接口 ----------------

@rule("MP-API-001", "warning", "接口", "非 HTTPS 请求",
      "请求地址用了 http://。小程序要求 request 合法域名且为 HTTPS（开发阶段可在开发者工具勾选不校验，提审前必须换）。")
def r_api_001(lines, text, path, ctx):
    if not path.endswith(".js"):
        return []
    return _line_hits("MP-API-001", lines, path, r"url\s*:\s*[\"']http://")


@rule("MP-DATA-001", "warning", "数据", "同步存储疑似在循环内调用",
      "wx.setStorageSync 出现在循环体内，同步 API 会阻塞页面渲染。改 wx.setStorage 异步版或移出循环。")
def r_data_001(lines, text, path, ctx):
    if not path.endswith(".js"):
        return []
    out = []
    for i, ln in enumerate(lines):
        if re.match(r"\s*for\s*\(", ln):
            window = "\n".join(lines[i:i + 10])
            if "wx.setStorageSync" in window:
                out.append(_mk("MP-DATA-001", path, i + 1, ln.strip()))
    return out


# ---------------- 页面质量 ----------------

@rule("MP-WXML-001", "nit", "页面质量", "图片未加 lazy-load",
      "<image> 未加 lazy-load 属性，长列表图片会一次性加载影响首屏。建议加上。")
def r_wxml_001(lines, text, path, ctx):
    if not path.endswith(".wxml"):
        return []
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"<image\b", ln) and "lazy-load" not in ln:
            out.append(_mk("MP-WXML-001", path, i + 1, ln.strip()))
    return out


# ---------------- 卫生 ----------------

@rule("MP-HYG-001", "warning", "卫生", "console.log 残留",
      "调试输出未清理。提审前删掉，或换成正式日志上报。")
def r_hyg_001(lines, text, path, ctx):
    if not path.endswith(".js"):
        return []
    return _line_hits("MP-HYG-001", lines, path, r"console\.(log|debug|info)\(")


@rule("MP-HYG-002", "blocker", "卫生", "错误被吞没",
      "空 catch 把错误吃了，出问题时无法定位。至少记日志或给用户友好提示。")
def r_hyg_002(lines, text, path, ctx):
    if not path.endswith(".js"):
        return []
    out = []
    rx = re.compile(r"catch\s*(\([^)]*\))?\s*\{\s*\}")
    for m in rx.finditer(text):
        lineno = text[:m.start()].count("\n") + 1
        snippet = lines[lineno - 1].strip()[:160] if lineno - 1 < len(lines) else ""
        out.append(_mk("MP-HYG-002", path, lineno, snippet))
    return out


@rule("MP-HYG-003", "warning", "卫生", "debugger 残留",
      "debugger 语句未删。提交前清掉。")
def r_hyg_003(lines, text, path, ctx):
    if not path.endswith(".js"):
        return []
    return _line_hits("MP-HYG-003", lines, path, r"\bdebugger\b")


# ---------------------------------------------------------------- 运行器

def run(target):
    files = collect_files(target)
    ctx = {"target": target, "files": files, "has_privacy_api": False, "all_text": ""}
    texts = {}
    for path in files:
        t = read_text(path)
        texts[path] = t
        ctx["all_text"] += "\n" + t
    if re.search(r"wx\.(onNeedPrivacyAuthorization|requirePrivacyAuthorize|openPrivacyContract)",
                 ctx["all_text"]):
        ctx["has_privacy_api"] = True

    findings = []
    for path in files:
        text = texts[path]
        lines = text.split("\n")
        rel = os.path.relpath(path, target)
        for r in RULES:
            try:
                for f in r["check"](lines, text, path, ctx) or []:
                    if f.file == path:
                        f.file = rel
                    findings.append(f)
            except Exception:
                continue
    return files, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="lhg-miniprogram 确定性提审审计")
    ap.add_argument("--target", default=".", help="扫描目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"], default="blocker")
    args = ap.parse_args(argv)

    target = os.path.abspath(args.target)
    if not os.path.isdir(target):
        print("target 不是目录：%s" % args.target, file=sys.stderr)
        return 1

    files, findings = run(target)

    sev_rank = {"blocker": 3, "warning": 2, "nit": 1}
    counts = {"blocker": 0, "warning": 0, "nit": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    result = {
        "tool": TOOL,
        "version": VERSION,
        "target": args.target,
        "summary": {
            "files_scanned": len(files),
            "rules_run": len(RULES),
            "blocker": counts["blocker"],
            "warning": counts["warning"],
            "nit": counts["nit"],
        },
        "findings": [f.to_dict() for f in sorted(
            findings, key=lambda x: (-sev_rank.get(x.severity, 0), x.file, x.line))],
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        s = result["summary"]
        print("小程序提审审计：扫描 %d 文件，运行 %d 条规则" % (s["files_scanned"], s["rules_run"]))
        print("blocker=%d warning=%d nit=%d" % (s["blocker"], s["warning"], s["nit"]))
        for f in result["findings"]:
            print("[%s][%s] %s:%d %s" % (
                f["severity"].upper(), f["rule_id"], f["file"], f["line"], f["title"]))
            print("    %s" % f["detail"])
            if f["snippet"]:
                print("    → %s" % f["snippet"])

    level = sev_rank[args.fail_on]
    bad = any(sev_rank.get(f.severity, 0) >= level for f in findings)
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
