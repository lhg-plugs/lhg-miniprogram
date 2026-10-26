<!-- About 简介（推送后填写到仓库 About 栏）：
小程序开发专家：一句话生成微信小程序 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-miniprogram
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, wechat-miniprogram, frontend -->

# lhg-miniprogram：小程序开发专家

> **一句话介绍**：给 AI 编程助手装上"小程序开发专家"——一句话需求变成页面规划、规范代码、接口联调方案，提审前 21 条确定性规则先查一遍，小白也能做出能提审的微信小程序。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-miniprogram
> /plugin install lhg-miniprogram@lhg-plugs
> ```

## 它是什么

`lhg-miniprogram` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **3 个命令**（小白入口）：`miniprogram` 一句话生成小程序，`miniprogram-page` 单页面生成，`miniprogram-audit` 提审前体检
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：需求规划、开发规范、接口联调、提审 checklist
- **2 个专家 agent**：小程序构建、独立审计
- **2 个硬门 hooks**：commit 前提审审计拦截、页面文件缺配对提醒（均可一键豁免）
- **21 条确定性提审规则**：纯 Python、零第三方依赖，5 秒出结果

技术栈：微信小程序原生（WXML / WXSS / JS）。

## 3 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-miniprogram:miniprogram` | 一句话 → 小程序（澄清→页面/接口规划→代码生成→自查→交付） | `/lhg-miniprogram:miniprogram "做个小区团购接龙"` |
| `/lhg-miniprogram:miniprogram-page` | 单页面生成（四件套 + 路由注册） | `/lhg-miniprogram:miniprogram-page "商品详情页"` |
| `/lhg-miniprogram:miniprogram-audit` | 提审前体检（脚本 + 人工 checklist） | `/lhg-miniprogram:miniprogram-audit` |

## 质量分档

- **默认 = 极速档**：流程完整、评审轮次少，确定性审计必跑。速度快、token 省，适合 MVP 与演示。
- **`--quality` = 品质档**：在 `miniprogram` 后加 `--quality`，增加提审条款深评审、独立审计复查、多轮打磨。**诚实说明**：品质档 token 消耗约为极速档的数倍，请确认接受再使用。

## 自查说明

自查 = 确定性脚本（机器）+ 人工提审 checklist（人）：

1. 先跑 `scripts/audit/mp_audit.py`（21 条规则），零 LLM 成本；
2. 发现分三级：**blocker**（必须修，commit 前 hook 会拦截）、**warning**（修或写豁免理由）、**nit**（顺手修）；
3. 再按 `lhg-mp-submit` skill 的提审 checklist 过一遍脚本抓不到的（隐私协议弹窗交互、iOS 虚拟支付按钮、真机体验）。

blocker 清零才算做完；为清零改规则算作弊，不许。

## 必须人工做的事（提前说清楚）

以下环节 AI 做不了，规划阶段就会列出来：

1. **AppID**：在微信公众平台注册小程序账号，拿到正式 AppID（`touristappid` 测试号不能提审）
2. **开发者工具**：亲手下载微信开发者工具，导入项目目录
3. **真机预览**：亲手扫码预览，真机行为（尤其 iOS）以实测为准
4. **隐私保护指引**：在公众平台填写，涉及用户信息时必须做
5. **提交审核**：亲手在开发者工具里点"上传"，并在公众平台提交审核

## 目录结构

```
lhg-miniprogram/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 3 个命令：miniprogram / miniprogram-page / miniprogram-audit
├── skills/                  # 4 个平台中立 skill（lhg-mp-plan/dev/api/submit）
├── agents/                  # 2 个专家 agent（mp-builder / mp-auditor）
├── hooks/                   # 2 个硬门（commit 前审计拦截 / 页面配对提醒）+ 豁免说明
├── scripts/audit/           # 21 条确定性提审规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你有个想法想做成微信小程序，但不想从头学 WXML/WXSS/JS 时 → 用 `/lhg-miniprogram:miniprogram`
- 你已经在做小程序，只想在提审前查一遍"会不会被打回"时 → 跑 `/lhg-miniprogram:miniprogram-audit`
- 你要给团队立一套"小程序代码也必须遵守"的纪律时 → 它的 hooks 硬门开箱即用

**什么时候不用：**

- 你希望 AI 帮你点"上传"和"提交审核"→ 做不到，微信开发者工具的操作和扫码预览必须人工完成
- 你希望"包过审"→ 承诺不了。审核规则以微信官方最新文档为准，本插件只做提审前检测
- 你做的是支付宝/抖音/快手小程序 → 本插件按微信小程序规范编写，其他平台需自己改规则
- 你的小程序强依赖原生插件、云开发特殊能力 → 规划时说明，本插件默认覆盖原生 + HTTP 接口场景

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-miniprogram](https://github.com/lhg-plugs/lhg-miniprogram) | 小程序开发专家：一句话生成微信小程序 | `/plugin install lhg-miniprogram@lhg-plugs` |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、21 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-miniprogram/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
