---
description: 单页面生成：给一个页面需求，生成小程序页面四件套（js/wxml/wxss/json）并注册到 app.json。
argument-hint: ["页面需求描述"]
---

# /lhg-miniprogram:miniprogram-page —— 单页面生成

用户输入在 `$ARGUMENTS` 中：`"页面需求描述"`。在已有小程序项目里新增一个页面（或重做一个页面）。

## 流程（加载 lhg-mp-dev 全程指导）

### 1. 澄清（最多 2 个问题）
只问真正影响页面结构的：页面路径（放哪个目录）、是不是 tabBar 页面、需要哪些接口。
信息够了直接开工，不要为凑数而问。

### 2. 生成四件套
按 lhg-mp-dev 第 3-4 节规范生成：
- `pages/<name>/<name>.js` —— Page({}) 结构，生命周期只写用得到的
- `pages/<name>/<name>.wxml` —— 语义化组件，图片加 lazy-load
- `pages/<name>/<name>.wxss` —— rpx 单位，样式按 BEM 式命名
- `pages/<name>/<name>.json` —— 按需（如自定义导航栏）

### 3. 注册路由
- 把页面路径追加到 `app.json` 的 `pages` 数组（tabBar 页面同时配 tabBar）。
- 检查：路径与文件目录一致，否则 MP-PAGE-001 会报 blocker。

### 4. 自查
跑一遍审计脚本（只看本页面相关 findings），blocker 清零；再按 lhg-mp-dev 第 6 节做页面级人工检查（空/错/加载三态、rpx 适配）。

## 硬规则
- 页面生成完不注册路由 → 不算做完。
- 业务逻辑里裸调网络接口 → 必须走 `utils/request.js` 统一封装。
- 需要用户登录态的页面 → 先确认登录方案（见 lhg-mp-api 第 4 节），不许脑补。
