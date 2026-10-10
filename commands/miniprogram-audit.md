---
description: 小程序提审前体检：跑确定性审计脚本 + 人工提审 checklist，输出分级报告并自动修复 blocker。
argument-hint: [项目目录] [--fix]
---

# /lhg-miniprogram:miniprogram-audit —— 提审前体检

用户输入在 `$ARGUMENTS` 中：`[项目目录] [--fix]`。目录缺省为当前项目根目录。

## 流程（加载 lhg-mp-submit 全程指导）

### 1. 跑脚本
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/mp_audit.py --target <目录> --format text
```
记下 blocker / warning / nit 的数量与明细（含文件、行号、规则说明）。

### 2. 分级与修复
- blocker：逐条修。`--fix` 缺省即自动修（最小改动原则）；修一条用脚本复查一条。
- 修不掉的（如需用户提供 AppID、隐私协议文案、类目资质）→ 列入"需人工处理"，不许为清零改规则。
- warning：修掉或写豁免理由（+有效期）；nit：顺手修。

### 3. 人工提审 checklist
按 lhg-mp-submit 第 5 节清单执行：
- 配置：AppID 是否为正式号（非 touristappid）、pages 是否注册完整
- 合规：隐私协议弹窗是否实现、隐私保护指引是否在公众平台填写
- 内容：有无敏感词、iOS 端有无虚拟商品支付按钮
- 包体积：主包/分包是否超限（以官方最新为准）

### 4. 输出报告
按 lhg-mp-submit 第 6 节模板输出自查报告，存为 `docs/audit-YYYYMMDD.md`，结论写清"可提审 / 暂不可提审"。

## 硬规则
- 有 blocker 就说"可提审" → 不许。
- 为清零改脚本规则或阈值 → 这是作弊，不许。
- **诚实边界**：脚本通过 ≠ 审核包过。审核是微信官方的人工/机器审核，规则会变，报告里必须写明这一点。
