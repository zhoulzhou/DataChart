const express = require('express');
const https = require('https');
const http = require('http');
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const { queryAll, queryOne, run } = require('../db');
const { authMiddleware } = require('../middleware/auth');

const router = express.Router();
router.use(authMiddleware);

const PY_SCRIPT = path.join(__dirname, '..', 'getData.py');
const EASTMONEY_URL = 'https://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get_cwgx.php';

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
  'totalEquity': '股东权益(亿)'
};

function httpGetJSON(url) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const mod = parsed.protocol === 'https:' ? https : http;
    const options = {
      hostname: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname + parsed.search,
      method: 'GET',
      timeout: 15000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Referer': 'https://eastmoney.com/',
        'Accept': 'application/json, text/plain, */*'
      }
    };

    console.log('[fetch] 请求东方财富:', url);

    const req = mod.request(options, (res) => {
      console.log('[fetch] 响应状态码:', res.statusCode);
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        console.log('[fetch] 响应长度:', data.length);
        if (res.statusCode >= 400) {
          return reject(new Error('HTTP ' + res.statusCode));
        }
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error('JSON解析失败: ' + data.substring(0, 300)));
        }
      });
    });
    req.on('timeout', () => { req.destroy(); reject(new Error('请求超时(15s)')); });
    req.on('error', (err) => reject(err));
    req.end();
  });
}

function fetchViaPython(code) {
  if (!fs.existsSync(PY_SCRIPT)) {
    console.log('[fetch] Python 脚本不存在:', PY_SCRIPT);
    return null;
  }
  try {
    console.log('[fetch] ====== 调用 Python Baostock ======');
    const result = execSync(`python3 ${PY_SCRIPT} ${code}`, {
      timeout: 60000,
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024
    });
    console.log('[fetch] Python 返回前 300 字符:', result.substring(0, 300));
    const parsed = JSON.parse(result);
    if (parsed && parsed.profit && parsed.profit.length > 0) {
      console.log('[fetch] Baostock: profit=' + parsed.profit.length +
        ', balance=' + (parsed.balance || []).length +
        ', cash=' + (parsed.cash_flow || []).length);
      return parsed;
    }
    return null;
  } catch (e) {
    console.log('[fetch] Python 调用失败:', e.message);
    return null;
  }
}

function fetchViaEastmoney(code) {
  return new Promise(async (resolve) => {
    try {
      console.log('[fetch] ====== 尝试东方财富 API ======');
      const arr = await httpGetJSON(
        `${EASTMONEY_URL}?type=Q&token=70f12f2f4f091e4e90272a310c76c5e&st=${code}&sr=&p=1&ps=200`
      );
      if (!Array.isArray(arr) || arr.length === 0) {
        console.log('[fetch] 东方财富返回空或非数组');
        resolve(null);
        return;
      }

      const profit = [];
      const balance = [];
      const cashFlow = [];

      for (const row of arr) {
        const sd = String(row.reportdate || '');
        const y = parseInt(sd.substring(0, 4));
        const m = parseInt(sd.substring(5, 7));
        const q = Math.floor((m - 1) / 3) + 1;
        const s = sd.substring(0, 10);
        const toYi = (v) => Math.round((parseFloat(v) || 0) / 100000000 * 10) / 10;

        profit.push({
          statDate: s, year: y, quarter: q,
          totalOperateIncome: toYi(row.businessincome),
          totalOperateCost: toYi(row.cost),
          netProfit: toYi(row.netprofit),
          totalEquity: toYi(row.equity)
        });

        balance.push({
          statDate: s, year: y, quarter: q,
          inventory: toYi(row.inventory),
          accountsReceivable: toYi(row.receivable),
          cashEquivalents: toYi(row.moneyfunds),
          tradingFinancialAssets: toYi(row.tradingasset),
          contractLiability: toYi(row.contractliability),
          totalEquity: toYi(row.equity)
        });

        cashFlow.push({
          statDate: s, year: y, quarter: q,
          operateCashFlow: toYi(row.operatecashflow)
        });
      }

      console.log('[fetch] 东方财富返回', arr.length, '条');
      resolve({ profit, balance, cash_flow: cashFlow });
    } catch (e) {
      console.log('[fetch] 东方财富 API 失败:', e.message);
      resolve(null);
    }
  });
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

router.post('/', async (_req, res) => {
  const { code } = _req.body;
  if (!code) {
    return res.json({ code: 1, message: '请输入股票代码' });
  }

  console.log('========== [fetch] 开始获取股票:', code, '==========');

  let data = null;
  let source = '';

  data = fetchViaPython(code);
  if (data && data.profit && data.profit.length > 0) {
    source = 'Baostock';
  } else {
    data = await fetchViaEastmoney(code);
    if (data && data.profit && data.profit.length > 0) {
      source = '东方财富';
    }
  }

  if (!data || !data.profit || data.profit.length === 0) {
    console.log('[fetch] 所有数据源均失败');
    return res.json({ code: 1, message: '未获取到数据：Baostock和东方财富均无返回' });
  }

  try {
    const companyId = ensureCompany(code);
    if (!companyId) {
      return res.json({ code: 1, message: '创建公司失败' });
    }

    let inserted = 0;
    let skipped = 0;

    for (const pRow of data.profit) {
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

    console.log('[fetch] 入库完成: 源=' + source + ', 新增=' + inserted + ', 跳过=' + skipped);
    console.log('========== [fetch] 完成 ==========');

    const fieldCount = queryAll(
      "SELECT COUNT(*) AS cnt FROM financial_fields WHERE report_id IN (SELECT id FROM financial_reports WHERE company_id = ?)",
      [companyId]
    );

    res.json({
      code: 0,
      message: `[${source}] 获取 ${data.profit.length} 条，新增 ${inserted} 条，跳过 ${skipped} 条`,
      data: { total: data.profit.length, inserted, skipped, source }
    });
  } catch (err) {
    console.log('[fetch] 入库异常:', err.stack || err.message);
    res.json({ code: 1, message: '入库失败: ' + err.message });
  }
});

module.exports = router;