const express = require('express');
const { queryAll, queryOne, run } = require('../db');
const { authMiddleware } = require('../middleware/auth');

const adminRouter = express.Router();
const publicRouter = express.Router();

adminRouter.use(authMiddleware);

function mergeReport(row) {
  const fields = queryAll(
    "SELECT source, field_name, field_value FROM financial_fields WHERE report_id = ?",
    [row.id]
  );

  function getField(name) {
    const f = fields.find(f => f.field_name === name);
    return (f && f.field_value != null) ? Number(f.field_value) : 0;
  }

  const revenue = getField('营业收入');
  const operatingCost = getField('营业成本');
  const grossProfit = getField('毛利') || (revenue - operatingCost);
  const cashTotal = getField('现金总额(含短期理财)') || (getField('货币资金') + getField('短期理财'));

  return {
    ...row,
    revenue,
    operating_cost: operatingCost,
    gross_profit: grossProfit,
    net_profit: getField('归母净利润'),
    operating_cash_flow: getField('经营活动现金流净额'),
    inventory: getField('存货'),
    accounts_receivable: getField('应收账款'),
    cash_total: cashTotal,
    contract_liabilities: getField('合同负债'),
    gross_margin: getField('毛利率(%)'),
    net_margin: getField('净利率(%)'),
    roe: getField('ROE(%)'),
    inventory_turnover_days: getField('存货周转天数'),
    ar_turnover_days: getField('应收周转天数')
  };
}

adminRouter.get('/', (req, res) => {
  const { company_id, year, quarter } = req.query;
  let sql = `
    SELECT r.*, c.name AS company_name, c.short_name AS company_short_name
    FROM financial_reports r
    JOIN companies c ON r.company_id = c.id
    WHERE 1=1
  `;
  const params = [];

  if (company_id) {
    sql += " AND r.company_id = ?";
    params.push(Number(company_id));
  }
  if (year) {
    sql += " AND r.year = ?";
    params.push(Number(year));
  }
  if (quarter) {
    sql += " AND r.quarter = ?";
    params.push(Number(quarter));
  }

  sql += " ORDER BY r.year DESC, r.quarter ASC";
  const rows = queryAll(sql, params);
  res.json({ code: 0, data: rows.map(mergeReport), message: 'ok' });
});

adminRouter.post('/', (req, res) => {
  return res.json({ code: 1, message: '请使用"获取数据"功能自动抓取，不再支持手动录入' });
});

adminRouter.put('/:id', (req, res) => {
  const { id } = req.params;
  const body = req.body;

  const record = queryOne("SELECT * FROM financial_reports WHERE id = ?", [id]);
  if (!record) {
    return res.json({ code: 1, message: '数据不存在' });
  }

  run(
    `UPDATE financial_reports SET year = ?, quarter = ?, updated_at = datetime('now','localtime') WHERE id = ?`,
    [
      body.year !== undefined ? body.year : record.year,
      body.quarter !== undefined ? body.quarter : record.quarter,
      id
    ]
  );

  res.json({ code: 0, message: '修改成功' });
});

adminRouter.delete('/:id', (req, res) => {
  const { id } = req.params;
  const record = queryOne("SELECT * FROM financial_reports WHERE id = ?", [id]);
  if (!record) {
    return res.json({ code: 1, message: '数据不存在' });
  }

  run("DELETE FROM financial_fields WHERE report_id = ?", [id]);
  run("DELETE FROM financial_reports WHERE id = ?", [id]);
  res.json({ code: 0, message: '删除成功' });
});

publicRouter.get('/', (req, res) => {
  const { company_id, year } = req.query;
  console.log('[public/financials] 请求 company_id:', company_id, 'year:', year);

  if (!company_id) {
    console.log('[public/financials] 缺少 company_id');
    return res.json({ code: 1, message: '参数不完整' });
  }

  const allYears = year === 'all';
  console.log('[public/financials] allYears:', allYears);

  let sql = `SELECT * FROM financial_reports
     WHERE company_id = ?`;
  const params = [Number(company_id)];

  if (!allYears) {
    sql += " AND year = ?";
    params.push(Number(year));
  }

  sql += " ORDER BY year ASC, quarter ASC";
  console.log('[public/financials] SQL:', sql, 'params:', params);
  const rows = queryAll(sql, params);
  console.log('[public/financials] 查询到 report 行数:', rows.length);

  const records = rows.map(mergeReport);
  records.forEach(r => r.period_type = 'quarterly');
  console.log('[public/financials] mergeReport 后记录数:', records.length);
  if (records.length > 0) {
    console.log('[public/financials] 首条:', JSON.stringify(records[0]));
    console.log('[public/financials] 末条:', JSON.stringify(records[records.length - 1]));
  }

  res.json({ code: 0, data: { type: 'quarterly', records }, message: 'ok' });
});

module.exports = adminRouter;
module.exports.publicRouter = publicRouter;