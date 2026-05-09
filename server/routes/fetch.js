const express = require('express');
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const { queryAll, queryOne, run } = require('../db');
const { authMiddleware } = require('../middleware/auth');

const router = express.Router();
router.use(authMiddleware);

const PY_SCRIPT = path.join(__dirname, '..', 'getData.py');

const FIELD_ALIASES = {
  'roeAvg': '净资产收益率(%)',
  'npMargin': '销售净利率(%)',
  'gpMargin': '销售毛利率(%)',
  'netProfit': '净利润(亿)',
  'epsTTM': '每股收益',
  'MBRevenue': '主营营业收入(亿)',
  'totalShare': '总股本',
  'liqaShare': '流通股本',
  'currentRatio': '流动比率',
  'quickRatio': '速动比率',
  'cashRatio': '现金比率',
  'YOYLiability': '股东权益增长率',
  'liabilityToAsset': '负债资产比率',
  'assetToEquity': '权益乘数',
  'CAToAsset': '流动资产/总资产',
  'NCAToAsset': '非流动资产/总资产',
  'tangibleAssetToAsset': '有形资产/总资产',
  'ebitToInterest': '已获利息倍数',
  'CFOToOR': '经营现金流/营业收入',
  'CFOToNP': '经营现金流/净利润',
  'CFOToGr': '经营现金流/营业总收入',
  'totalOperateIncome': '营业收入(亿)',
  'totalOperateCost': '营业成本(亿)',
  'operateCashFlow': '经营活动现金流量(亿)',
  'inventory': '存货(亿)',
  'accountsReceivable': '应收账款(亿)',
  'cashEquivalents': '货币资金(亿)',
  'tradingFinancialAssets': '交易性金融资产(亿)',
  'contractLiability': '合同负债(亿)',
  'totalEquity': '股东权益(亿)',
  '营业收入': '营业收入(亿)',
  '营业成本': '营业成本(亿)',
  '毛利': '毛利(亿)',
  '毛利率(%)': '毛利率(%)',
  '归母净利润': '归母净利润(亿)',
  '净利率(%)': '净利率(%)',
  'ROE(%)': 'ROE(%)',
  '货币资金': '货币资金(亿)',
  '短期理财': '短期理财(亿)',
  '现金总额(含短期理财)': '现金总额(亿)',
  '存货': '存货(亿)',
  '存货周转率': '存货周转率',
  '应收账款': '应收账款(亿)',
  '应收周转率': '应收周转率',
  '经营现金流': '经营现金流(亿)',
  '合同负债': '合同负债(亿)',
  '股东权益': '股东权益(亿)'
};

function fetchViaPython(code) {
  if (!fs.existsSync(PY_SCRIPT)) {
    console.log('[fetch] Python 脚本不存在:', PY_SCRIPT);
    return null;
  }
  try {
    console.log('[fetch] ====== 调用 Python yfinance ======');
    const result = execSync(`python3 ${PY_SCRIPT} ${code}`, {
      timeout: 120000,
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024
    });
    console.log('[fetch] Python 返回前 300 字符:', result.substring(0, 300));
    const parsed = JSON.parse(result);
    if (parsed && parsed.source && parsed.source !== 'none') {
      console.log('[fetch] 数据源:', parsed.source,
        ', records=' + (parsed.records ? parsed.records.length : parsed.profit ? parsed.profit.length : 0));
      return parsed;
    }
    return null;
  } catch (e) {
    console.log('[fetch] Python 调用失败:', e.message);
    return null;
  }
}

function findByYq(arr, year, quarter) {
  if (!arr) return null;
  return arr.find(r => r.year === year && r.quarter === quarter) || null;
}

function ensureCompany(code) {
  let company = queryOne("SELECT id FROM companies WHERE short_name = ?", [code]);
  if (company) return company.id;
  run("INSERT INTO companies (name, short_name, status) VALUES (?, ?, 'enabled')", [code, code]);
  company = queryOne("SELECT id FROM companies WHERE short_name = ?", [code]);
  return company ? company.id : null;
}

function insertFields(reportId, obj, source) {
  if (!obj) return;
  const skipKeys = new Set(['year', 'quarter', 'statDate', 'code', 'pubDate', 'roeAvg', 'npMargin', 'gpMargin', 'epsTTM', 'totalShare', 'liqaShare']);
  for (const [key, val] of Object.entries(obj)) {
    if (skipKeys.has(key)) continue;
    const n = parseFloat(val);
    if (isNaN(n)) continue;
    const alias = FIELD_ALIASES[key] || null;
    run("INSERT INTO financial_fields (report_id, source, field_name, field_value, field_alias) VALUES (?, ?, ?, ?, ?)",
      [reportId, source, key, Math.round(n * 10) / 10, alias]);
  }
}

function insertFieldsFlat(reportId, record, source) {
  const skipKeys = new Set(['year', 'quarter', 'statDate']);
  for (const [key, val] of Object.entries(record)) {
    if (skipKeys.has(key)) continue;
    const n = parseFloat(val);
    if (isNaN(n)) continue;
    const alias = FIELD_ALIASES[key] || key;
    run("INSERT INTO financial_fields (report_id, source, field_name, field_value, field_alias) VALUES (?, ?, ?, ?, ?)",
      [reportId, source, key, Math.round(n * 10) / 10, alias]);
  }
}

router.post('/', async (_req, res) => {
  const { code } = _req.body;
  if (!code) {
    return res.json({ code: 1, message: '请输入股票代码' });
  }

  console.log('========== [fetch] 开始获取股票:', code, '==========');

  const data = fetchViaPython(code);

  if (!data) {
    return res.json({ code: 1, message: 'Python 脚本执行失败，未获取到数据' });
  }

  const { source, records, profit } = data;
  const isYfinance = source === 'yfinance' && records && records.length > 0;
  const isBaostock = source === 'baostock' && profit && profit.length > 0;

  if (!isYfinance && !isBaostock) {
    console.log('[fetch] 所有数据源均无数据');
    return res.json({ code: 1, message: '未获取到数据：yfinance和Baostock均无返回' });
  }

  try {
    const companyId = ensureCompany(code);
    if (!companyId) {
      return res.json({ code: 1, message: '创建公司失败' });
    }

    let inserted = 0;
    let skipped = 0;
    const total = isYfinance ? records.length : profit.length;

    if (isYfinance) {
      for (const r of records) {
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

        insertFieldsFlat(report.id, r, 'yfinance');
        inserted++;
      }
    } else {
      for (const pRow of profit) {
        const year = pRow.year;
        const quarter = pRow.quarter;
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

        insertFields(report.id, pRow, 'profit');
        insertFields(report.id, findByYq(data.balance, year, quarter), 'balance');
        insertFields(report.id, findByYq(data.cash_flow, year, quarter), 'cash_flow');
        inserted++;
      }
    }

    console.log('[fetch] 入库完成: 源=' + source + ', 新增=' + inserted + ', 跳过=' + skipped);
    console.log('========== [fetch] 完成 ==========');

    res.json({
      code: 0,
      message: `[${source}] 获取 ${total} 条，新增 ${inserted} 条，跳过 ${skipped} 条`,
      data: { total, inserted, skipped, source }
    });
  } catch (err) {
    console.log('[fetch] 入库异常:', err.stack || err.message);
    res.json({ code: 1, message: '入库失败: ' + err.message });
  }
});

module.exports = router;