---
name: lhg-mp-api
description: 小程序接口联调规范：网络统一封装、登录态（wx.login 换 openid）、错误处理、联调 checklist。前后端联调前加载。
license: MIT
compatibility: 适用于任何支持 Markdown 指令的 AI 编程助手（Claude Code、豆包、Workbuddy 等）
metadata:
  version: 1.0.0
  author: 刘洪光
---

# lhg-mp-api：接口联调规范

> 目标：小程序端与服务端的接口"一次联调通过"——契约先行、封装统一、错误可查。
> 核心纪律：**业务代码不许裸调网络接口；所有外部输入先校验再用。**

## 1. 何时使用

- 规划/实现小程序的网络请求时 → 加载本 skill
- 实现微信登录、手机号授权时 → 看第 4 节
- 联调出问题（调不通、数据对不上）时 → 按第 5 节 checklist 排查

## 2. 输入与输出

- **输入**：接口清单（来自 lhg-mp-plan 第 5 步）
- **输出**：`utils/request.js` 统一封装 + 各页面的接口调用代码 + 联调报告

## 3. 网络统一封装

### 3.1 封装要求

所有网络请求必须走 `utils/request.js`，它要干这几件事：

1. **拼 baseURL**：从全局配置读，区分开发/体验/正式环境，不许在业务代码里写死域名。
2. **带登录态**：自动在 header 里带 token（见第 4 节），token 过期自动走刷新或重新登录。
3. **统一错误形状**：把服务端的错误转成 `{code, message}`，业务代码只判断 code。
4. **超时与重试**：默认超时 10 秒；GET 请求失败可重试 1 次，POST 不许自动重试（防重复下单）。
5. **loading 管理**：支持传入 `loading: true` 自动展示/关闭加载中，避免每个页面手写。

### 3.2 业务代码调用示例（示意）

```js
const { request } = require('../../utils/request.js');

async loadData() {
  this.setData({ loading: true, error: '' });
  try {
    const res = await request({ url: '/v1/items', data: { page: 1 } });
    this.setData({ list: res.data.items });
  } catch (err) {
    this.setData({ error: err.message || '加载失败' });
  } finally {
    this.setData({ loading: false });
  }
}
```

### 3.3 封装纪律

- 业务代码里出现 `wx.request` → 必须收敛到 `request()`，这是硬规则。
- 接口地址用相对路径（`/v1/items`），baseURL 只在封装层出现一次。
- 敏感信息（token、手机号）不许打进日志。

### 3.4 接口契约卡片模板

每个接口在动手前先写一张契约卡片，贴进 PLAN.md：

```markdown
### POST /v1/orders（创建订单）
- 登录：需要
- 请求：{ items: [{id, qty}], address_id: string, idempotency_key: string }
- 响应：{ code: 0, data: { order_id, pay_params } } / { code: 非0, message }
- 幂等：Idempotency-Key 头，后端按 key 去重
```

契约卡片是前后端并行的基础：小程序端按卡片写调用，服务端按卡片实现，联调时对不上先查卡片。

## 4. 登录态方案

### 4.1 微信登录标准流程

1. 小程序端调 `wx.login()` 拿到 `code`。
2. 把 `code` 发给**自己的服务端**，服务端用 `code + appid + appsecret` 换 `openid` / `session_key`。
3. 服务端生成自己的登录 token 返回给小程序端，小程序端存 storage，后续请求带上。

### 4.2 铁律

- **appsecret 只能在服务端**：出现在小程序代码里就是 MP-SEC-001 blocker，提审前必须清掉。
- **不强制登录**：用户拒绝授权也能用核心功能（隐私合规要求），登录只在必要时触发。
- **手机号按需索取**：`getPhoneNumber` 只在真正需要时调用，不许进页面就弹。

### 4.3 登录状态管理

- token 存 `wx.setStorageSync('token', token)`，封装层每次请求自动带上。
### 4.4 token 刷新策略

1. **短 token + 刷新**：access token 有效期 2 小时，refresh token 7 天；401 时先用 refresh token 换新的，换不到再跳登录页。
2. **并发去重**：多个请求同时 401 时，只刷新一次，其他请求排队等新 token（否则会触发登录风控）。
3. **退出登录**：清 token + 清用户信息缓存，回到首页，不要留在需要登录的页面上。

## 5. 联调 checklist（调不通时按顺序查）

1. **域名**：公众平台后台是否配置了 request 合法域名？开发阶段是否勾选了"不校验合法域名"？
2. **HTTPS**：正式环境接口是不是 HTTPS？（MP-API-001 会报 http）
3. **契约**：请求字段名、类型与服务端文档是否一致？（大小写、必填项）
4. **登录态**：需要登录的接口，header 里带 token 了吗？token 过期了吗？
5. **跨域**：小程序没有浏览器跨域问题，调不通先看服务端日志，别在小程序侧瞎猜。
6. **真机差异**：开发者工具里能调通、真机不行 → 查域名配置与 TLS 版本，真机以实测为准。
7. **时间**：服务端返回的时间戳是秒还是毫秒？差 1000 倍的 bug 最常见。
8. **分页**：列表接口的 `page/limit` 与服务端是否一致？第一页 page 从 0 还是 1 开始？
9. **图片**：图片 URL 是不是 HTTPS？防盗链的 CDN 在小程序里能打开吗？
10. **版本号**：联调的是哪个环境（开发/体验/正式）？baseURL 切对了吗？

### 5.5 联调报告模板

联调完输出一份小报告，贴进交付文档：

```markdown
## 联调报告
- 接口总数：X，通过 Y，阻塞 Z
- 阻塞项：<接口> —— <原因> —— <需要谁处理>
- 与契约的偏差：<有/无，有则列出>
```

## 6. 反模式（不要这么做）

- ❌ 每个页面手写 `wx.request`——改域名时要改 20 处
- ❌ POST 失败自动重试——用户会被重复扣款/下单
- ❌ 把 appsecret 写进小程序代码——等于把家门钥匙贴在门上
- ❌ 进页面就强制要手机号——隐私合规会打回，体验也差
- ❌ 联调时猜——先看网络面板的实际请求与响应，再下结论

## 7. 自检与反馈

每次执行完本 skill，做一次轻量自检（不额外输出打扰用户）：

1. 是否还有裸调 `wx.request` 的业务代码？→ 收敛到封装层。
2. 登录流程里 appsecret 是否只在服务端？→ 出现在前端立即删。
3. POST 接口是否有防重复机制？→ 没有就加上（幂等键或按钮防抖）。
4. 联调 checklist 是否逐项过过？→ 没过的项写进交付报告的"需人工处理"。

如发现本 skill 自身的方法论缺陷，按以下流程反馈：

- **标准冒烟用例**：用"商品列表接口联调"走一遍本 skill，检查封装层是否统一、登录态是否通、错误是否有统一形状。
- **一键提 issue**：确认问题后，以 `[QC] <一句话问题>` 为标题、正文写清"复现输入 → 错误输出 → 期望输出"，提交到 https://github.com/lhg-plugs/lhg-miniprogram/issues。

## 出品：刘洪光

本 skill 由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
