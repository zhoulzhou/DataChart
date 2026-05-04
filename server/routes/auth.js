const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { queryOne } = require('../db');
const { authMiddleware, JWT_SECRET } = require('../middleware/auth');

const router = express.Router();

router.post('/login', (req, res) => {
  const { username, password } = req.body;
  if (!username || !password) {
    return res.json({ code: 1, message: '请输入账号和密码' });
  }

  const user = queryOne("SELECT * FROM admin_users WHERE username = ?", [username]);
  if (!user) {
    return res.json({ code: 1, message: '账号或密码错误' });
  }

  const valid = bcrypt.compareSync(password, user.password);
  if (!valid) {
    return res.json({ code: 1, message: '账号或密码错误' });
  }

  const token = jwt.sign(
    { id: user.id, username: user.username },
    JWT_SECRET,
    { expiresIn: '24h' }
  );

  res.json({ code: 0, data: { token }, message: '登录成功' });
});

router.get('/check', authMiddleware, (req, res) => {
  res.json({ code: 0, data: { username: req.user.username }, message: 'ok' });
});

module.exports = router;
