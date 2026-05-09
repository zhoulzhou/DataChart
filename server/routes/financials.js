const express = require('express');
const { queryAll, queryOne, run } = require('../db');
const { authMiddleware } = require('../middleware/auth');

const adminRouter = express.Router();
const publicRouter = express.Router();

adminRouter.use(authMiddleware);

function mergeReport(row) {
  const profit = JSON.parse(row.profit_data || '{}');
  const balance = JSON.parse(row.balance_data || '{}');
  const cashFlow = JSON.parse(row.cash_flow_data || '{}');

  const revenue = profit.totalOperateIncome || 0;
  const operatingCost = profit.totalOperateCost || 0;

  return {
    ...row,
    revenue,
    operating_cost: operatingCost,
    gross_profit: revenue - operatingCost,
    net_profit: profit.netProfit || 0,
    operating_cash_flow: cashFlow.operateCashFlow || 0,
    inventory: balance.inventory || 0,
    accounts_receivable: balance.accountsReceivable || 0,
    cash_total: (balance.cashEquivalents || 0) + (balance.tradingFinancialAssets || 0),
    contract_liabilities: balance.contractLiability || 0
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

  run("DELETE FROM financial_reports WHERE id = ?", [id]);
  res.json({ code: 0, message: '删除成功' });
});

publicRouter.get('/', (req, res) => {
  const { company_id, year } = req.query;

  if (!company_id) {
    return res.json({ code: 1, message: '参数不完整' });
  }

  const allYears = year === 'all';

  let sql = `SELECT * FROM financial_reports
     WHERE company_id = ?`;
  const params = [Number(company_id)];

  if (!allYears) {
    sql += " AND year = ?";
    params.push(Number(year));
  }

  sql += " ORDER BY year ASC, quarter ASC";
  const rows = queryAll(sql, params);

  const records = rows.map(mergeReport);
  records.forEach(r => r.period_type = 'quarterly');

  res.json({ code: 0, data: { type: 'quarterly', records }, message: 'ok' });
});

module.exports = adminRouter;
module.exports.publicRouter = publicRouter;