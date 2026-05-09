## 验证清单

- [x] 后端 `/api/fetch-financials` 接口可接收 `{ code }` 并返回正确结果
- [x] 东方财富 API 调用正确（URL 参数包含 type=Q, st=股票代码）
- [x] `reportdate` 正确解析为 year 和 quarter
- [x] 字段映射与 spec 一致（9 个字段 + 2 个计算字段）
- [x] 所有数值保留 1 位小数
- [x] 公司不存在时自动创建（name/short_name 用股票代码）
- [x] 公司已存在时复用已有 ID
- [x] 同一 company_id + year + quarter 不重复入库
- [x] 返回结果包含 total/inserted/skipped 统计
- [x] 接口需要登录认证（authMiddleware）
- [x] 前端 StockFetch.vue 页面可正常显示
- [x] 输入框可输入股票代码，按钮可触发获取
- [x] 加载中状态正确显示
- [x] 成功/失败提示信息正确展示
- [x] 导航栏「获取数据」链接可跳转到对应页面
- [x] 页面路由 `/admin/stock-fetch` 需登录才能访问
