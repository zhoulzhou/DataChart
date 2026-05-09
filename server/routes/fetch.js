const express = require('express');
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const { queryOne, run } = require('../db');
const { authMiddleware } = require('../middleware/auth');

const router = express.Router();
router.use(authMiddleware);

const PY_SCRIPT = path.join(__dirname, '..', 'getData.py');

const FIELD_ALIASES = {
  '营业收入': '营业收入(亿)',
  '营业成本': '营业成本(亿)',
  '归母净利润': '归母净利润(亿)',
  '存货': '存货(亿)',
  '应收账款': '应收账款(亿)',
  '货币资金': '货币资金(亿)',
  '短期理财': '短期理财(亿)',
  '合同负债': '合同负债(亿)',
  '股东权益': '股东权益(亿)',
  '经营活动现金流净额': '经营活动现金流净额(亿)'
};

function fetchViaPython(code) {
  if (!fs.existsSync(PY_SCRIPT)) {
    console.log('[fetch] Python 脚本不存在:', PY_SCRIPT);
    return null;
  }
  try {
    console.log('[fetch] ====== 调用 Python (yfinance + baostock) ======');
    const output = execSync(`python3 "${PY_SCRIPT}" ${code} 2>&1`, {
      timeout: 180000,
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024,
      windowsHide: true
    });

    const lines = output.trim().split('\n');

    let jsonLine = null;
    for (let i = lines.length - 1; i >= 0; i--) {
      const trimmed = lines[i].trim();
      if (trimmed.startsWith('{')) {
        jsonLine = trimmed;
        break;
      }
    }

    if (!jsonLine) {
      console.log('[fetch] 未找到 JSON 输出');
      return null;
    }

    const parsed = JSON.parse(jsonLine);

    const yfRecords = parsed?.yfinance?.records || [];
    const bsRecords = parsed?.baostock?.records || [];
    console.log(`[fetch] Yahoo: ${yfRecords.length} 条  |  Baostock: ${bsRecords.length} 条`);
    console.log(`[fetch] 使用 Yahoo 数据入库`);
    console.log('');

    return { yfRecords, bsRecords };
  } catch (e) {
    console.log('[fetch] Python 调用失败:', e.message);
    return null;
  }
}

function ensureCompany(code) {
  let company = queryOne("SELECT id FROM companies WHERE short_name = ?", [code]);
  if (company) return company.id;
  run("INSERT INTO companies (name, short_name, status) VALUES (?, ?, 'enabled')", [code, code]);
  company = queryOne("SELECT id FROM companies WHERE short_name = ?", [code]);
  return company ? company.id : null;
}

function insertFields(reportId, record) {
  const skipKeys = new Set(['year', 'quarter', 'statDate']);
  for (const [key, val] of Object.entries(record)) {
    if (skipKeys.has(key)) continue;
    const n = parseFloat(val);
    if (isNaN(n)) continue;
    const alias = FIELD_ALIASES[key] || key;
    run("INSERT INTO financial_fields (report_id, source, field_name, field_value, field_alias) VALUES (?, ?, ?, ?, ?)",
      [reportId, 'yfinance', key, Math.round(n * 10) / 10, alias]);
  }
}

router.post('/', async (_req, res) => {
  const { code } = _req.body;
  if (!code) {
    return res.json({ code: 1, message: '请输入股票代码' });
  }

  console.log('========== [fetch] 开始获取股票:', code, '==========');

  const data = fetchViaPython(code);

  if (!data || !data.yfRecords || data.yfRecords.length === 0) {
    console.log('[fetch] Yahoo 未获取到数据');
    return res.json({ code: 1, message: 'Yahoo 未获取到数据' });
  }

  const { yfRecords, bsRecords } = data;

  try {
    const companyId = ensureCompany(code);
    if (!companyId) {
      return res.json({ code: 1, message: '创建公司失败' });
    }

    let inserted = 0;
    let skipped = 0;

    for (const r of yfRecords) {
      const year = r.year;
      const quarter = r.quarter;
      if (!year || !quarter) continue;

      const existing = queryOne(
        "SELECT id FROM financial_reports WHERE company_id = ? AND year = ? AND quarter = ?",
        [companyId, year, quarter]
      );
      if (existing) { skipped++; continue; }

      run("INSERT INTO financial_reports (company_id, year, quarter) VALUES (?, ?, ?)",
        [companyId, year, quarter]);

      const report = queryOne(
        "SELECT id FROM financial_reports WHERE company_id = ? AND year = ? AND quarter = ?",
        [companyId, year, quarter]
      );
      if (!report) continue;

      insertFields(report.id, r);
      inserted++;
    }

    console.log('[fetch] 入库完成: Yahoo新增=' + inserted + ', 跳过=' + skipped + ', Baostock对比=' + bsRecords.length + '条');
    console.log('========== [fetch] 完成 ==========');

    res.json({
      code: 0,
      message: `Yahoo ${yfRecords.length} 条  Baostock ${bsRecords.length} 条  新增 ${inserted} 条  跳过 ${skipped} 条`,
      data: {
        yahoo: yfRecords.length,
        baostock: bsRecords.length,
        inserted,
        skipped
      }
    });
  } catch (err) {
    console.log('[fetch] 入库异常:', err.stack || err.message);
    res.json({ code: 1, message: '入库失败: ' + err.message });
  }
});

module.exports = router;