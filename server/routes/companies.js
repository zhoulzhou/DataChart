const express = require('express');
const { queryAll, queryOne, run } = require('../db');
const { authMiddleware } = require('../middleware/auth');

const adminRouter = express.Router();
const publicRouter = express.Router();

adminRouter.use(authMiddleware);

adminRouter.get('/', (req, res) => {
  const { status } = req.query;
  let sql = "SELECT * FROM companies";
  const params = [];

  if (status) {
    sql += " WHERE status = ?";
    params.push(status);
  }

  sql += " ORDER BY id DESC";
  const rows = queryAll(sql, params);
  res.json({ code: 0, data: rows, message: 'ok' });
});

adminRouter.post('/', (req, res) => {
  const { name, short_name } = req.body;
  if (!name || !short_name) {
    return res.json({ code: 1, message: '公司名称和简称不能为空' });
  }

  const dup = queryOne("SELECT id FROM companies WHERE short_name = ?", [short_name]);
  if (dup) {
    return res.json({ code: 1, message: '公司简称已存在，请使用其他简称' });
  }

  run("INSERT INTO companies (name, short_name) VALUES (?, ?)", [name, short_name]);
  res.json({ code: 0, message: '添加成功' });
});

adminRouter.put('/:id', (req, res) => {
  const { id } = req.params;
  const { name, short_name } = req.body;

  const company = queryOne("SELECT * FROM companies WHERE id = ?", [id]);
  if (!company) {
    return res.json({ code: 1, message: '公司不存在' });
  }

  if (short_name && short_name !== company.short_name) {
    const dup = queryOne("SELECT id FROM companies WHERE short_name = ? AND id != ?", [short_name, id]);
    if (dup) {
      return res.json({ code: 1, message: '公司简称已存在，请使用其他简称' });
    }
  }

  run(
    "UPDATE companies SET name = ?, short_name = ? WHERE id = ?",
    [name || company.name, short_name || company.short_name, id]
  );
  res.json({ code: 0, message: '修改成功' });
});

adminRouter.put('/:id/status', (req, res) => {
  const { id } = req.params;
  const { status } = req.body;

  if (!['enabled', 'disabled'].includes(status)) {
    return res.json({ code: 1, message: '状态值无效' });
  }

  const company = queryOne("SELECT * FROM companies WHERE id = ?", [id]);
  if (!company) {
    return res.json({ code: 1, message: '公司不存在' });
  }

  run("UPDATE companies SET status = ? WHERE id = ?", [status, id]);
  res.json({ code: 0, message: status === 'enabled' ? '已启用' : '已停用' });
});

adminRouter.delete('/:id', (req, res) => {
  const { id } = req.params;
  const company = queryOne("SELECT * FROM companies WHERE id = ?", [id]);
  if (!company) {
    return res.json({ code: 1, message: '公司不存在' });
  }

  const hasData = queryOne("SELECT id FROM financial_data WHERE company_id = ? LIMIT 1", [id]);
  if (hasData) {
    return res.json({ code: 1, message: '该公司下存在财务数据，无法删除。请先删除相关数据' });
  }

  run("DELETE FROM companies WHERE id = ?", [id]);
  res.json({ code: 0, message: '删除成功' });
});

publicRouter.get('/', (req, res) => {
  const rows = queryAll(
    "SELECT id, name, short_name FROM companies WHERE status = 'enabled' ORDER BY id DESC"
  );
  res.json({ code: 0, data: rows, message: 'ok' });
});

module.exports = adminRouter;
module.exports.publicRouter = publicRouter;
