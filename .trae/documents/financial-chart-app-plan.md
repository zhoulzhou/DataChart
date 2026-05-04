# 多公司财务指标可视化网页 — 完整开发计划

***

## 一、项目概述

基于 Vue 3 + ECharts + SQLite 构建多公司财务指标可视化系统，分为**后台管理端**（需登录，录/改/删数据）和**前台展示端**（无需登录，看图表）。

***

## 二、技术架构

| 层级       | 技术选型                                          | 说明          |
| -------- | --------------------------------------------- | ----------- |
| 前端       | Vue 3 + Vite + Vue Router + ECharts 5 + Axios | SPA 单页应用    |
| 后端       | Node.js + Express + better-sqlite3            | RESTful API |
| 数据库      | SQLite（单文件 `data.db`）                         | 免运维，复制即备份   |
| 认证       | JWT（jsonwebtoken）                             | 后台管理端登录态    |
| 密码加密     | bcryptjs                                      | 管理员密码哈希存储   |

**项目目录结构：**

```
DataChart/
├── server/                      # 后端服务
│   ├── package.json
│   ├── index.js                 # Express 入口，启动服务
│   ├── db.js                    # SQLite 初始化 + 建表
│   ├── middleware/
│   │   └── auth.js              # JWT 认证中间件
│   ├── routes/
│   │   ├── auth.js              # 登录相关路由
│   │   ├── companies.js         # 公司管理路由
│   │   └── financials.js        # 财务数据路由
│   └── data.db                  # SQLite 数据库文件（自动生成）
├── client/                      # 前端应用
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── router/
│       │   └── index.js
│       ├── api/
│       │   ├── request.js       # Axios 实例（baseURL、拦截器）
│       │   ├── auth.js          # 登录 API
│       │   ├── companies.js     # 公司 API
│       │   └── financials.js    # 财务数据 API
│       ├── views/
│       │   ├── public/
│       │   │   └── Dashboard.vue        # 前台展示首页
│       │   └── admin/
│       │       ├── Login.vue            # 登录页
│       │       ├── CompanyManage.vue    # 公司管理
│       │       ├── DataEntry.vue        # 数据录入
│       │       └── DataList.vue         # 数据列表
│       ├── components/
│       │   ├── KpiCards.vue             # 关键指标数字卡片
│       │   ├── RevenueNetProfitChart.vue  # 营收+净利折线图
│       │   ├── RevenueGrossChart.vue    # 营收毛利柱状图
│       │   ├── InventoryReceivableChart.vue  # 存货应收走势图
│       │   └── ProfitRateChart.vue      # 毛利率/净利率比例图
│       └── assets/
│           └── style.css                # 全局样式+响应式
├── package.json                 # 根 package.json（启动脚本）
└── .trae/
    └── documents/
        └── financial-chart-app-plan.md  # 本文档
```

***

## 三、数据库设计

### 表 1：companies（公司信息表）

| 字段          | 类型      | 约束                                    | 说明                 |
| ----------- | ------- | ------------------------------------- | ------------------ |
| id          | INTEGER | PRIMARY KEY AUTOINCREMENT             | 主键                 |
| name        | TEXT    | NOT NULL                              | 公司全称               |
| short\_name | TEXT    | NOT NULL                              | 公司简称               |
| status      | TEXT    | NOT NULL DEFAULT 'enabled'            | enabled / disabled |
| created\_at | TEXT    | DEFAULT (datetime('now','localtime')) | 创建时间               |

### 表 2：financial\_data（财务指标数据表）

| 字段                    | 类型      | 约束                                    | 说明        |
| --------------------- | ------- | ------------------------------------- | --------- |
| id                    | INTEGER | PRIMARY KEY AUTOINCREMENT             | 主键        |
| company\_id           | INTEGER | NOT NULL REFERENCES companies(id)     | 所属公司      |
| year                  | INTEGER | NOT NULL                              | 年份        |
| month                 | INTEGER | NOT NULL                              | 月份 (1-12) |
| revenue               | REAL    | NOT NULL DEFAULT 0                    | 营业收入      |
| gross\_profit         | REAL    | NOT NULL DEFAULT 0                    | 毛利        |
| net\_profit           | REAL    | NOT NULL DEFAULT 0                    | 净利        |
| operating\_cash\_flow | REAL    | NOT NULL DEFAULT 0                    | 经营现金流     |
| inventory             | REAL    | NOT NULL DEFAULT 0                    | 存货        |
| accounts\_receivable  | REAL    | NOT NULL DEFAULT 0                    | 应收账款      |
| created\_at           | TEXT    | DEFAULT (datetime('now','localtime')) | 创建时间      |
| updated\_at           | TEXT    | DEFAULT (datetime('now','localtime')) | 更新时间      |

**唯一约束：** `UNIQUE(company_id, year, month)` — 同公司同年同月不可重复

### 表 3：admin\_users（管理员账号表）

| 字段          | 类型      | 约束                                    | 说明          |
| ----------- | ------- | ------------------------------------- | ----------- |
| id          | INTEGER | PRIMARY KEY AUTOINCREMENT             | 主键          |
| username    | TEXT    | NOT NULL UNIQUE                       | 账号          |
| password    | TEXT    | NOT NULL                              | bcrypt 加密密码 |
| created\_at | TEXT    | DEFAULT (datetime('now','localtime')) | 创建时间        |

**默认账号：** 首次启动时自动创建 `admin` / `admin123`

***

## 四、后端 API 设计

### 基准路径：`/api`

### 4.1 认证模块

| 方法   | 路径          | 认证 | 说明              |
| ---- | ----------- | -- | --------------- |
| POST | /auth/login | 否  | 登录，返回 JWT token |
| GET  | /auth/check | 是  | 验证 token 有效性    |

**POST /auth/login 请求体：**

```json
{ "username": "admin", "password": "admin123" }
```

**响应：**

```json
{ "code": 0, "data": { "token": "xxx" }, "message": "登录成功" }
```

### 4.2 公司管理模块（需认证）

| 方法   | 路径                    | 说明                            |
| ---- | --------------------- | ----------------------------- |
| GET  | /companies            | 获取公司列表（支持 ?status=enabled 过滤） |
| POST | /companies            | 新增公司                          |
| PUT  | /companies/:id        | 编辑公司名称/简称                     |
| PUT  | /companies/:id/status | 启用/停用公司                       |

**POST /companies 请求体：**

```json
{ "name": "某某科技有限公司", "short_name": "某某科技" }
```

### 4.3 财务数据模块（需认证）

| 方法     | 路径                 | 说明                                    |
| ------ | ------------------ | ------------------------------------- |
| GET    | /financials        | 查询列表（支持 ?company\_id=\&year=\&month=） |
| POST   | /financials        | 新增一条财务数据                              |
| PUT    | /financials/:id    | 编辑一条财务数据                              |
| DELETE | /financials/:id    | 删除一条财务数据                              |

### 4.4 公开 API（无需认证）

| 方法  | 路径                 | 说明                                   |
| --- | ------------------ | ------------------------------------ |
| GET | /public/companies  | 获取已启用的公司列表                           |
| GET | /public/financials | 获取指定公司+年份的财务数据（?company\_id=\&year=） |

**统一响应格式：**

```json
{ "code": 0, "data": ..., "message": "ok" }
```

code=0 表示成功，非 0 表示错误。

***

## 五、前端路由设计

| 路径                | 组件                | 权限  | 说明     |
| ----------------- | ----------------- | --- | ------ |
| /                 | Dashboard.vue     | 公开  | 前台展示首页 |
| /login            | Login.vue         | 公开  | 管理员登录页 |
| /admin/companies  | CompanyManage.vue | 需登录 | 公司管理   |
| /admin/data-entry | DataEntry.vue     | 需登录 | 数据录入   |
| /admin/data-list  | DataList.vue      | 需登录 | 数据列表   |

**路由守卫：** `/admin/*` 路径进入前检查 localStorage 中是否有 token，无则跳转 `/login`。

***

## 六、前端组件设计

### 6.1 Dashboard.vue（前台展示首页）

* 顶部：公司下拉选择 + 年份下拉选择

* 中部：KpiCards 数字卡片行

* 下方：4 个 ECharts 图表组件，2x2 网格布局

* 切换公司/年份时，所有数据联动刷新

### 6.2 KpiCards.vue

* Props: `cardsData` (包含 6 项指标数值)

* 显示为响应式卡片网格

### 6.3 图表组件（均接收 props，watch 变化后刷新）

* **RevenueNetProfitChart.vue** — 营业收入 + 净利 月度趋势折线图（双 Y 轴）

* **RevenueGrossChart.vue** — 营收与毛利对比柱状图

* **InventoryReceivableChart.vue** — 存货、应收账款月度走势对比图

* **ProfitRateChart.vue** — 毛利率/净利率比例图（可选折线图）

### 6.4 Login.vue

* 账号密码表单，调用登录 API，成功后将 token 存入 localStorage 并跳转 `/admin/companies`

### 6.5 CompanyManage.vue

* 公司列表表格 + 新增/编辑弹窗

* 启用/停用开关

### 6.6 DataEntry.vue

* 级联下拉：公司 → 年份 → 月份

* 6 项指标输入表单

* 保存按钮，重复校验提示

### 6.7 DataList.vue

* 筛选条件行（公司、年份、月份）

* 数据表格（分页），每行支持编辑/删除

***

## 七、响应式适配方案

* 使用 CSS Grid / Flexbox 弹性布局

* 图表区域：桌面端 2 列，移动端（<768px）1 列堆叠

* KpiCards：桌面端 6 列，平板 3 列，手机 2 列

* 使用 `vw` / `%` 百分比 + `max-width` 控制图表容器

***

## 八、详细实施步骤（共 9 个阶段）

### 阶段 1：项目初始化与目录搭建

1. 创建 `server/` 和 `client/` 目录结构
2. 初始化 `server/package.json`（安装 express, better-sqlite3, cors, jsonwebtoken, bcryptjs）
3. 初始化 `client/` 通过 `npm create vite@latest client -- --template vue`（安装 vue-router, axios, echarts）
4. 创建根 `package.json`（scripts 同时启动前后端）
5. 配置 `vite.config.js`（proxy 代理 /api 到后端 3000 端口）

### 阶段 2：数据库初始化

1. 编写 `server/db.js`：建表逻辑（companies, financial\_data, admin\_users）
2. 首次启动自动创建默认管理员 `admin/admin123`（bcrypt 加密）
3. 在 `server/index.js` 中调用数据库初始化

### 阶段 3：后端 — 认证模块

1. 编写 `server/middleware/auth.js`（JWT 验证中间件）
2. 编写 `server/routes/auth.js`（login、check 接口）

### 阶段 4：后端 — 公司管理 API

1. 编写 `server/routes/companies.js`（CRUD + 状态切换）
2. 公开接口 `/public/companies` 获取启用公司列表

### 阶段 5：后端 — 财务数据 API

1. 编写 `server/routes/financials.js`（CRUD + 唯一性校验）
2. 公开接口 `/public/financials` 获取图表用数据

### 阶段 6：前端 — 基础框架搭建

1. 配置 Vue Router（含路由守卫）
2. 配置 Axios（baseURL、请求拦截器自动带 token、响应拦截器处理 401）
3. 编写 API 层文件（auth.js, companies.js, financials.js）
4. 编写全局样式 `style.css`

### 阶段 7：前端 — 后台管理页面

1. 实现 Login.vue
2. 实现 CompanyManage.vue
3. 实现 DataEntry.vue
4. 实现 DataList.vue

### 阶段 8：前端 — 前台展示页面

1. 实现 Dashboard.vue（公司/年份选择 + 数据加载）
2. 实现 KpiCards.vue
3. 实现 4 个图表组件

### 阶段 9：联调测试与验证

1. 前后端联调，确认 API 数据流通
2. 验证文档中的全部测试用例
3. 修复问题并完善

***

## 九、验证文档（测试用例）

### 9.1 后台管理端测试

| 编号  | 测试场景                   | 预期结果               |
| --- | ---------------------- | ------------------ |
| T01 | 未登录访问 /admin/companies | 自动跳转到 /login       |
| T02 | 使用错误密码登录               | 提示"账号或密码错误"        |
| T03 | 使用 admin/admin123 登录   | 登录成功，跳转到公司管理页      |
| T04 | 新增公司"测试公司"             | 列表中出现新公司，状态为"启用"   |
| T05 | 编辑公司名称                 | 公司名称更新成功           |
| T06 | 停用公司                   | 状态变为"停用"，前台选择列表不显示 |
| T07 | 录入一条财务数据               | 保存成功，提示"保存成功"      |
| T08 | 同公司同年同月再次录入            | 提示"该月数据已存在"        |
| T09 | 编辑已有财务数据               | 修改成功，数据更新          |
| T10 | 删除一条财务数据               | 删除成功，列表中移除         |
| T11 | 按公司+年份筛选数据列表           | 只显示符合条件的数据         |
| T12 | 停用公司后录入数据时不可选          | 公司下拉列表中不显示已停用公司    |

### 9.2 前台展示端测试

| 编号  | 测试场景         | 预期结果             |
| --- | ------------ | ---------------- |
| T14 | 直接访问 /       | 无需登录即可查看         |
| T15 | 选择公司下拉       | 只显示"启用"状态的公司     |
| T16 | 选择公司+年份后数字卡片 | 显示最新月份或汇总的 6 项指标 |
| T17 | 折线图显示营收+净利   | 按 1-12 月展示双折线    |
| T18 | 柱状图显示营收毛利    | 按月份对比柱状图         |
| T19 | 走势图显示存货应收    | 按月份双线对比          |
| T20 | 切换公司         | 所有图表+卡片同步刷新      |
| T21 | 切换年份         | 所有图表+卡片同步刷新      |
| T22 | 图表悬浮         | 显示具体数值 tooltip   |
| T23 | 手机端浏览器访问     | 图表堆叠为单列，卡片适配手机宽度 |
| T24 | 无数据年份        | 图表显示空状态提示        |

***

## 十、数据流说明

```
用户操作（前台）
  ↓ 选择公司 + 年份
Dashboard.vue
  ↓ 调用 GET /api/public/financials?company_id=X&year=Y
后端 Express
  ↓ 查询 SQLite
返回 JSON 数据
  ↓
KpiCards（最新月份汇总值）
4 个 Chart 组件（12 个月数组数据）
  ↓
ECharts 渲染图表
```

```
用户操作（后台）
  ↓ POST /api/financials
后端 Express
  ↓ 校验唯一性 → 写入 SQLite
返回成功
  ↓
前台刷新时自动获取最新数据
```

***

## 十一、开发顺序优先级

1. **后端优先**：数据库 → 认证 → API → 确保接口可用（可用 Postman 验证）
2. **前端跟进**：框架 → API 层 → 后台页面 → 前台页面
3. **联调收尾**：端到端测试 → 修 bug → 交付

***

