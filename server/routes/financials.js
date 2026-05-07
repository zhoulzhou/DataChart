const express = require('express');
const { queryAll, queryOne, run } = require('../db');
const { authMiddleware } = require('../middleware/auth');

const adminRouter = express.Router();
const publicRouter = express.Router();

adminRouter.use(authMiddleware);

adminRouter.get('/', (req, res) => {
  const { company_id, year, month, quarter, period_type } = req.query;
  let sql = `
    SELECT f.*, c.name AS company_name, c.short_name AS company_short_name
    FROM financial_data f
    JOIN companies c ON f.company_id = c.id
    WHERE 1=1
  `;
  const params = [];

  if (company_id) {
    sql += " AND f.company_id = ?";
    params.push(Number(company_id));
  }
  if (year) {
    sql += " AND f.year = ?";
    params.push(Number(year));
  }
  if (month) {
    sql += " AND f.month = ?";
    params.push(Number(month));
  }
  if (quarter) {
    sql += " AND f.quarter = ?";
    params.push(Number(quarter));
  }
  if (period_type === 'monthly') {
    sql += " AND f.month IS NOT NULL";
  }
  if (period_type === 'quarterly') {
    sql += " AND f.quarter IS NOT NULL";
  }

  sql += " ORDER BY f.year DESC, f.month ASC, f.quarter ASC";
  const rows = queryAll(sql, params);
  res.json({ code: 0, data: rows, message: 'ok' });
});

const FINANCIAL_FIELDS = [
  'revenue', 'operating_cost', 'gross_profit', 'net_profit',
  'operating_cash_flow', 'inventory', 'accounts_receivable',
  'cash_total', 'contract_liabilities'
];

adminRouter.post('/', (req, res) => {
  const {
    company_id, year, month, quarter, period_type,
    revenue, operating_cost, gross_profit, net_profit,
    operating_cash_flow, inventory, accounts_receivable,
    cash_total, contract_liabilities
  } = req.body;

  if (!company_id || !year) {
    return res.json({ code: 1, message: '公司和年份不能为空' });
  }

  const vals = {
    revenue: revenue || 0,
    operating_cost: operating_cost || 0,
    gross_profit: gross_profit || 0,
    net_profit: net_profit || 0,
    operating_cash_flow: operating_cash_flow || 0,
    inventory: inventory || 0,
    accounts_receivable: accounts_receivable || 0,
    cash_total: cash_total || 0,
    contract_liabilities: contract_liabilities || 0
  };

  if (period_type === 'quarterly') {
    if (!quarter) {
      return res.json({ code: 1, message: '请选择季度' });
    }
    const existing = queryAll(
      "SELECT id FROM financial_data WHERE company_id = ? AND year = ? AND quarter = ?",
      [company_id, year, quarter]
    );
    if (existing.length > 0) {
      return res.json({ code: 1, message: '该季度数据已存在，请勿重复录入' });
    }
    run(`
      INSERT INTO financial_data
      (company_id, year, month, quarter, revenue, operating_cost, gross_profit, net_profit,
       operating_cash_flow, inventory, accounts_receivable, cash_total, contract_liabilities)
      VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      company_id, year, quarter,
      vals.revenue, vals.operating_cost, vals.gross_profit, vals.net_profit,
      vals.operating_cash_flow, vals.inventory, vals.accounts_receivable,
      vals.cash_total, vals.contract_liabilities
    ]);
  } else {
    if (!month) {
      return res.json({ code: 1, message: '请选择月份' });
    }
    const existing = queryAll(
      "SELECT id FROM financial_data WHERE company_id = ? AND year = ? AND month = ?",
      [company_id, year, month]
    );
    if (existing.length > 0) {
      return res.json({ code: 1, message: '该月数据已存在，请勿重复录入' });
    }
    run(`
      INSERT INTO financial_data
      (company_id, year, month, quarter, revenue, operating_cost, gross_profit, net_profit,
       operating_cash_flow, inventory, accounts_receivable, cash_total, contract_liabilities)
      VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      company_id, year, month,
      vals.revenue, vals.operating_cost, vals.gross_profit, vals.net_profit,
      vals.operating_cash_flow, vals.inventory, vals.accounts_receivable,
      vals.cash_total, vals.contract_liabilities
    ]);
  }

  res.json({ code: 0, message: '保存成功' });
});

adminRouter.put('/:id', (req, res) => {
  const { id } = req.params;
  const body = req.body;

  const record = queryOne("SELECT * FROM financial_data WHERE id = ?", [id]);
  if (!record) {
    return res.json({ code: 1, message: '数据不存在' });
  }

  run(`
    UPDATE financial_data SET
      year = ?, month = ?, quarter = ?,
      revenue = ?, operating_cost = ?, gross_profit = ?, net_profit = ?,
      operating_cash_flow = ?, inventory = ?, accounts_receivable = ?,
      cash_total = ?, contract_liabilities = ?,
      updated_at = datetime('now','localtime')
    WHERE id = ?
  `, [
    body.year !== undefined ? body.year : record.year,
    body.month !== undefined ? body.month : record.month,
    body.quarter !== undefined ? body.quarter : record.quarter,
    body.revenue !== undefined ? body.revenue : record.revenue,
    body.operating_cost !== undefined ? body.operating_cost : record.operating_cost,
    body.gross_profit !== undefined ? body.gross_profit : record.gross_profit,
    body.net_profit !== undefined ? body.net_profit : record.net_profit,
    body.operating_cash_flow !== undefined ? body.operating_cash_flow : record.operating_cash_flow,
    body.inventory !== undefined ? body.inventory : record.inventory,
    body.accounts_receivable !== undefined ? body.accounts_receivable : record.accounts_receivable,
    body.cash_total !== undefined ? body.cash_total : record.cash_total,
    body.contract_liabilities !== undefined ? body.contract_liabilities : record.contract_liabilities,
    id
  ]);

  res.json({ code: 0, message: '修改成功' });
});

adminRouter.delete('/:id', (req, res) => {
  const { id } = req.params;
  const record = queryOne("SELECT * FROM financial_data WHERE id = ?", [id]);
  if (!record) {
    return res.json({ code: 1, message: '数据不存在' });
  }

  run("DELETE FROM financial_data WHERE id = ?", [id]);
  res.json({ code: 0, message: '删除成功' });
});

publicRouter.get('/', (req, res) => {
  const { company_id, year, period_type } = req.query;

  if (!company_id) {
    return res.json({ code: 1, message: '参数不完整' });
  }

  const allYears = year === 'all';

  if (period_type === 'quarterly') {
    let sql = `SELECT * FROM financial_data
       WHERE company_id = ? AND quarter IS NOT NULL`;
    const params = [Number(company_id)];
    if (!allYears) {
      sql += " AND year = ?";
      params.push(Number(year));
    }
    sql += " ORDER BY year ASC, quarter ASC";
    const rows = queryAll(sql, params);
    return res.json({ code: 0, data: { type: 'quarterly', records: rows }, message: 'ok' });
  }

  let sql = `SELECT * FROM financial_data
     WHERE company_id = ? AND month IS NOT NULL`;
  const params = [Number(company_id)];
  if (!allYears) {
    sql += " AND year = ?";
    params.push(Number(year));
  }
  sql += " ORDER BY year ASC, month ASC";
  const rows = queryAll(sql, params);
  res.json({ code: 0, data: { type: 'monthly', records: rows }, message: 'ok' });
});

module.exports = adminRouter;
module.exports.publicRouter = publicRouter;
