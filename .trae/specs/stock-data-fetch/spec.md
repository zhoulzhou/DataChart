# 股票财务数据自动获取 Spec

## Why
后台手动录入财务数据效率低。A 股上市公司财报数据可通过东方财富隐藏 API 自动获取，直接导入数据库，减少人工录入工作量。

## What Changes
- 新增后端路由 `/api/fetch-financials`，接收股票代码，调用东方财富 API 获取季度财报
- 自动将股票代码注册为公司（如果不存在），简称用股票代码
- 根据 `reportDate` 解析年份和季度，存入 `financial_data` 表
- 字段映射：API 返回字段 → 数据库字段，自动计算毛利和现金总额
- 同一公司 + 同年 + 同季度不重复入库（存在则跳过）
- 前端新增「获取财务数据」页面：输入股票代码 → 点击获取 → 显示入库结果
- 导航栏新增入口

## Impact
- Affected specs: 无（新功能）
- Affected code:
  - `server/routes/fetch.js`（新增）
  - `server/index.js`（注册新路由）
  - `client/src/views/admin/StockFetch.vue`（新增）
  - `client/src/router/index.js`（新增路由）
  - `client/src/App.vue`（新增导航链接）

## ADDED Requirements

### Requirement: 股票财务数据获取
系统 SHALL 支持输入 A 股股票代码，自动从东方财富 API 获取季度财报并存入数据库。

#### Scenario: 成功获取并入库
- **WHEN** 管理员输入有效股票代码并点击"获取"
- **THEN** 系统调用东方财富 API，返回该股票近 3 年季度财报
- **THEN** 自动创建公司记录（如果该代码尚未注册）
- **THEN** 将每条季度数据按字段映射写入 `financial_data` 表
- **THEN** 页面显示入库结果：获取 X 条，新增 Y 条，跳过 Z 条

#### Scenario: 股票代码无效
- **WHEN** 输入无效股票代码
- **THEN** 返回错误提示，不修改数据库

#### Scenario: 数据已存在
- **WHEN** 同一公司 + 同年 + 同季度数据已入库
- **THEN** 跳过该条，不重复写入，并在结果中显示"跳过"

### Requirement: 字段映射规则
系统 SHALL 按以下规则将 API 数据映射到数据库字段：

| API 字段 | 数据库字段 | 说明 |
|----------|-----------|------|
| `businessincome` (东方财富) | `revenue` | 营业收入 |
| `cost` (东方财富) | `operating_cost` | 营业成本 |
| 计算：`revenue - operating_cost` | `gross_profit` | 毛利 |
| `netprofit` (东方财富) | `net_profit` | 归母净利润 |
| `operatecashflow` (东方财富) | `operating_cash_flow` | 经营现金流净额 |
| `inventory` | `inventory` | 存货 |
| `receivable` (东方财富) | `accounts_receivable` | 应收账款 |
| 计算：`moneyfunds + tradingasset` | `cash_total` | 现金总额 = 货币资金 + 交易性金融资产 |
| `contractliability` (东方财富) | `contract_liabilities` | 合同负债 |

#### Scenario: reportDate 解析
- **WHEN** API 返回 `reportdate: "2025-03-31 00:00:00"`
- **THEN** 解析出 `year=2025, quarter=1`（3月对应Q1, 6月对应Q2, 9月对应Q3, 12月对应Q4）

#### Scenario: 数值精度
- **WHEN** 写入数据库
- **THEN** 所有数值保留 1 位小数（按 `getData.txt` 要求）

### Requirement: 自动注册公司
系统 SHALL 在获取数据时自动创建公司记录。

#### Scenario: 股票代码首次使用
- **WHEN** 股票代码 `300308` 首次获取数据
- **THEN** 自动创建公司：`name="300308", short_name="300308", status="enabled"`

#### Scenario: 股票代码已存在
- **WHEN** 公司表中已存在该 `short_name`
- **THEN** 使用已有公司 ID，不重复创建

### Requirement: 防重复入库
系统 SHALL 防止同一公司同年同季度数据重复。

#### Scenario: 再次获取已有数据
- **WHEN** 再次获取同一股票代码
- **THEN** 已存在的 `company_id + year + quarter` 组合跳过不写入
- **THEN** 仅写入新增的季度数据
