---
name: lhg-mp-dev
description: 微信小程序开发规范：WXML/WXSS/JS 四件套结构、组件与生命周期、页面路由、本地存储、小程序特有坑位。写小程序代码前加载。
license: MIT
compatibility: 适用于任何支持 Markdown 指令的 AI 编程助手（Claude Code、豆包、Workbuddy 等）
metadata:
  version: 1.0.0
  author: 刘洪光
---

# lhg-mp-dev：小程序开发规范

> 目标：生成的小程序代码"一次写对"——结构规范、路由不错、避开小程序特有坑。
> 本 skill 的规范要点来自微信小程序公开文档的公开知识（未复制原文），实现细节为原创总结。

## 1. 何时使用

- 生成/修改小程序页面、组件、全局配置时 → 加载本 skill
- 用户问"小程序里 X 怎么做"时 → 按本 skill 的对应章节回答
- 提审前自查时 → 对照第 6 节做页面级人工检查

## 2. 输入与输出

- **输入**：页面清单（来自 lhg-mp-plan）+ 具体页面需求
- **输出**：页面四件套代码（`.js` / `.wxml` / `.wxss` / `.json` 按需）+ 路由注册

## 3. 工程结构（约定大于配置）

```
miniprogram/
├── app.js            # 全局逻辑：登录态初始化、全局数据
├── app.json          # 全局配置：pages / window / tabBar / subpackages
├── app.wxss          # 全局样式
├── project.config.json  # 工程配置：appid（提审前换正式号）
├── sitemap.json      # 搜索索引配置（按需）
├── pages/            # 页面：每个页面独立目录，四件套
│   └── index/
│       ├── index.js    # Page({}) 逻辑
│       ├── index.wxml  # 结构
│       ├── index.wxss  # 样式（rpx 单位）
│       └── index.json  # 页面配置（按需，如自定义导航栏）
├── components/       # 自定义组件：Component({}) 四件套
└── utils/
    └── request.js    # 网络统一封装（见 lhg-mp-api）
```

### 3.1 四件套纪律

1. **同名同目录**：`pages/detail/detail.js` + `detail.wxml` + `detail.wxss` + `detail.json`，差一个字符都是 bug。
2. **.js 必需、.wxml 必需**：逻辑与结构缺一不可；`.wxss` / `.json` 按需，没有就不建空文件凑数。
3. **写完必注册**：页面路径追加到 `app.json` 的 `pages` 数组，否则 MP-PAGE-001 会报 blocker。

## 4. 页面与组件写法

### 4.1 Page 结构

```js
Page({
  data: { list: [], loading: true, error: '' },
  onLoad(options) { /* 取页面参数，只做轻量初始化 */ },
  onShow() { /* 每次展示时刷新（如从详情页返回） */ },
  onPullDownRefresh() { /* 下拉刷新：调接口，完事调 wx.stopPullDownRefresh() */ },
  onReachBottom() { /* 上拉加载更多 */ },
  onShareAppMessage() { /* 需要分享才写 */ },
  // 自定义方法放后面，按"事件处理 → 数据请求 → 工具"分组
});
```

纪律：
- 生命周期只写用得到的，不写空函数凑数。
- `onLoad` 只做轻量初始化，重型请求放 `onShow` 或用户触发后（首屏更快）。
- 页面参数通过 `onLoad(options)` 取，取完先做合法性校验。

### 4.2 组件写法

- 可复用的 UI（商品卡片、空状态、加载骨架）抽成 `components/` 下的自定义组件，用 `Component({})`。
- 组件通信：父→子用 `properties`，子→父用 `triggerEvent`，不许跨层级直接改父级 data。

### 4.3 路由纪律

- `wx.navigateTo`：普通页面跳转（页面栈最多 10 层，超了会失败）。
- `wx.redirectTo`：关闭当前页再跳（登录成功后跳首页用这个）。
- `wx.switchTab`：**tabBar 页面只能用这个**，用 navigateTo 会失败（MP-RTE-001 会报 warning）。
- `wx.navigateBack`：返回，带 `delta` 跨多级返回。
### 4.4 分包与按需加载

1. **主包只放 tabBar 页**：首页、核心 tab 页放主包，其他按业务拆分包（`subpackages`）。
2. **分包预下载**：可能紧接着访问的分包配 `preloadRule`，体验更顺。
3. **独立分包慎用**：独立分包不能依赖主包资源，除非你明确知道在干什么。
4. **图片走 CDN**：大图、banner 图放 CDN，不打进代码包（包体积是提审硬门槛）。

### 4.5 页面参数校验

`onLoad(options)` 拿到的参数一律视为外部输入：

- 必填参数缺失 → 跳回上一页并提示，不许带着 undefined 往下跑。
- id 类参数先校验格式（数字/长度），再调接口。

## 5. 样式与适配

1. **单位用 rpx**：750rpx = 屏幕宽，写死 px 的地方必须能说出理由。
2. **安全区**：有底部操作栏的页面处理 iPhone 安全区（`env(safe-area-inset-bottom)`）。
3. **图片加 lazy-load**：长列表的 `<image>` 必须加 `lazy-load`（MP-WXML-001 会检查）。
4. **三态齐全**：每个列表页都要有"加载中 / 空数据 / 加载失败"三种状态，不许只有成功态。
5. **骨架屏**：首屏数据请求慢的页面用骨架屏占位，比白屏+转圈体验好。
6. **字体**：中文字体用系统默认，不引入大体积自定义字体（包体积杀手）。

## 6. 小程序特有坑位（提审前必查）

| 坑 | 说明 |
|---|---|
| 隐私协议 | 涉及用户信息必须实现同意弹窗（`wx.onNeedPrivacyAuthorization` 等），且在公众平台填写《隐私保护指引》，否则提审打回 |
| 测试号 AppID | `touristappid` 不能提审，提审前换正式 AppID（MP-APP-003 会提醒） |
| request 域名 | 正式环境 request 必须 HTTPS 且在公众平台配置合法域名 |
| 分包 | 主包超 2MB 启发式警告（MP-SIZE-001）；大图片放 CDN，不打进包 |
| iOS 虚拟支付 | iOS 端小程序内不许卖虚拟商品（会员/课程/道具），否则可能被封支付接口 |
| 同步 API | `wx.setStorageSync` 等同步 API 别在循环里调，会卡页面（MP-DATA-001） |
| appsecret | 永远不许出现在前端代码里（MP-SEC-001 是 blocker） |
| 页面栈 | `navigateTo` 最多 10 层，列表→详情→下单这种链条用 `redirectTo` 及时释放 |
| 下拉刷新 | 开了 `enablePullDownRefresh` 的页面，请求完成后必须调 `wx.stopPullDownRefresh()`，否则一直转 |
| 表单 | 提交按钮加防抖/禁用态，防止用户连点导致重复提交 |

## 7. 反模式（不要这么做）

- ❌ 页面写完不注册路由——等于没写
- ❌ 业务代码里裸调网络接口——必须走 `utils/request.js`（见 lhg-mp-api）
- ❌ `onLoad` 里塞五个串行请求——首屏慢到用户关掉
- ❌ 文案里编造数字/评价——诚实是底线
- ❌ 承诺"包过审"——审核规则以微信官方最新为准

## 8. 自检与反馈

每次执行完本 skill，做一次轻量自检（不额外输出打扰用户）：

1. 生成的页面四件套是否齐全、路径与 app.json 一致？→ 不一致立即修。
2. 是否有裸调网络接口？→ 必须收敛到 `utils/request.js`。
3. 列表页三态是否齐全？→ 缺了补上。
4. 是否写了"包过审"类承诺？→ 删掉，换成诚实表述。

如发现本 skill 自身的方法论缺陷，按以下流程反馈：

- **标准冒烟用例**：用"生成一个商品列表页"走一遍本 skill，检查四件套是否齐全、路由是否注册、三态是否有、审计脚本是否零 blocker。
- **一键提 issue**：确认问题后，以 `[QC] <一句话问题>` 为标题、正文写清"复现输入 → 错误输出 → 期望输出"，提交到 https://github.com/lhg-plugs/lhg-miniprogram/issues。

## 出品：刘洪光

本 skill 由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
