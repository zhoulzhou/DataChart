# Tasks

- [x] Task 1: 创建后端数据获取路由 `server/routes/fetch.js`
  - 实现 `POST /api/fetch-financials` 接口
  - 调用东方财富隐藏 API `http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get_cwgx.php` 获取季度财报
  - 自动注册公司：查询 `companies` 表，`short_name` 不存在则插入
  - 根据 `reportdate` 字段解析 `year` 和 `quarter`（3/6/9/12月 → Q1/Q2/Q3/Q4）
  - 字段映射写入 `financial_data`：
    - `businessincome` → `revenue`
    - `cost` → `operating_cost`
    - 计算 `gross_profit = revenue - operating_cost`
    - `netprofit` → `net_profit`
    - `operatecashflow` → `operating_cash_flow`
    - `inventory` → `inventory`
    - `receivable` → `accounts_receivable`
    - `moneyfunds + tradingasset` → `cash_total`
    - `contractliability` → `contract_liabilities`
  - 所有数值 `Math.round(v * 10) / 10` 保留 1 位小数
  - 防重复：`company_id + year + quarter` 已存在则跳过
  - 返回 `{ code: 0, data: { total, inserted, skipped } }`
  - 需要 `authMiddleware` 认证

- [x] Task 2: `server/index.js` 注册新路由
  - `const fetchRoutes = require('./routes/fetch')`
  - `app.use('/api/fetch-financials', fetchRoutes)`

- [x] Task 3: 创建前端页面 `client/src/views/admin/StockFetch.vue`
  - 输入框：股票代码
  - 「获取数据」按钮，点击后显示加载状态
  - 调用 `POST /api/fetch-financials`，body 传 `{ code }`
  - 结果展示：获取 X 条，新增 Y 条，跳过 Z 条
  - 成功后提示可前往数据列表查看

- [x] Task 4: `client/src/router/index.js` 注册新路由
  - 导入 `StockFetch` 组件
  - 新增路由 `{ path: '/admin/stock-fetch', name: 'StockFetch', component: StockFetch, meta: { requiresAuth: true } }`

- [x] Task 5: `client/src/App.vue` 添加导航链接
  - 在导航栏添加 `<router-link to="/admin/stock-fetch">获取数据</router-link>`

# Task Dependencies
- Task 2 depends on Task 1
- Task 3, Task 4, Task 5 互相独立，可并行
