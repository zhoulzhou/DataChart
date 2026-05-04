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

adminRouter.post('/', (req, res) => {
  const {
    company_id, year, month, quarter, period_type,
    revenue, gross_profit, net_profit,
    operating_cash_flow, inventory, accounts_receivable
  } = req.body;

  if (!company_id || !year) {
    return res.json({ code: 1, message: '公司和年份不能为空' });
  }

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
      (company_id, year, month, quarter, revenue, gross_profit, net_profit,
       operating_cash_flow, inventory, accounts_receivable)
      VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
    `, [
      company_id, year, quarter,
      revenue || 0, gross_profit || 0, net_profit || 0,
      operating_cash_flow || 0, inventory || 0, accounts_receivable || 0
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
      (company_id, year, month, quarter, revenue, gross_profit, net_profit,
       operating_cash_flow, inventory, accounts_receivable)
      VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
    `, [
      company_id, year, month,
      revenue || 0, gross_profit || 0, net_profit || 0,
      operating_cash_flow || 0, inventory || 0, accounts_receivable || 0
    ]);
  }

  res.json({ code: 0, message: '保存成功' });
});

adminRouter.put('/:id', (req, res) => {
  const { id } = req.params;
  const {
    revenue, gross_profit, net_profit,
    operating_cash_flow, inventory, accounts_receivable
  } = req.body;

  const record = queryOne("SELECT * FROM financial_data WHERE id = ?", [id]);
  if (!record) {
    return res.json({ code: 1, message: '数据不存在' });
  }

  run(`
    UPDATE financial_data SET
      revenue = ?, gross_profit = ?, net_profit = ?,
      operating_cash_flow = ?, inventory = ?, accounts_receivable = ?,
      updated_at = datetime('now','localtime')
    WHERE id = ?
  `, [
    revenue !== undefined ? revenue : record.revenue,
    gross_profit !== undefined ? gross_profit : record.gross_profit,
    net_profit !== undefined ? net_profit : record.net_profit,
    operating_cash_flow !== undefined ? operating_cash_flow : record.operating_cash_flow,
    inventory !== undefined ? inventory : record.inventory,
    accounts_receivable !== undefined ? accounts_receivable : record.accounts_receivable,
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

  if (!company_id || !year) {
    return res.json({ code: 1, message: '参数不完整' });
  }

  if (period_type === 'quarterly') {
    const rows = queryAll(
      `SELECT * FROM financial_data
       WHERE company_id = ? AND year = ? AND quarter IS NOT NULL
       ORDER BY quarter ASC`,
      [Number(company_id), Number(year)]
    );
    return res.json({ code: 0, data: { type: 'quarterly', records: rows }, message: 'ok' });
  }

  const rows = queryAll(
    `SELECT * FROM financial_data
     WHERE company_id = ? AND year = ? AND month IS NOT NULL
     ORDER BY month ASC`,
    [Number(company_id), Number(year)]
  );
  res.json({ code: 0, data: { type: 'monthly', records: rows }, message: 'ok' });
});

module.exports = adminRouter;
module.exports.publicRouter = publicRouter;
