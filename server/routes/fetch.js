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
    console.log('[fetch] FATAL: Python 脚本不存在:', PY_SCRIPT);
    return null;
  }
  try {
    console.log('[fetch] ====== 执行 Python ======');
    console.log(`[fetch] CMD: python3 "${PY_SCRIPT}" ${code}`);
    const output = execSync(`python3 "${PY_SCRIPT}" ${code} 2>&1`, {
      timeout: 180000,
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024,
      windowsHide: true
    });
    console.log('[fetch] Python 进程退出码: 0');
    return parseOutput(output);
  } catch (e) {
    console.log('[fetch] Python 进程退出码非0:', e.status);
    console.log('[fetch] 错误摘要:', e.message ? e.message.substring(0, 200) : 'none');
    const partial = (e && e.stdout) ? e.stdout : '';
    if (partial) {
      console.log('[fetch] === Python 部分输出 ===');
      console.log(partial.substring(0, 3000));
      console.log('[fetch] === 输出结束 ===');
      return parseOutput(partial);
    }
    console.log('[fetch] FATAL: Python 完全无输出');
    return null;
  }
}

function parseOutput(rawOutput) {
  if (!rawOutput || !rawOutput.trim()) {
    console.log('[fetch] 输出为空');
    return null;
  }

  const lines = rawOutput.trim().split('\n');

  let jsonStartIdx = -1;
  for (let i = lines.length - 1; i >= 0; i--) {
    const trimmed = lines[i].trim();
    if (trimmed.startsWith('{')) {
      jsonStartIdx = i;
      break;
    }
  }

  if (jsonStartIdx > 0) {
    const debugLines = lines.slice(0, jsonStartIdx);
    console.log('[fetch] === Python 调试日志 (stderr) ===');
    for (const l of debugLines) {
      if (l.trim()) console.log('[py] ' + l.trim());
    }
    console.log('[fetch] === 日志结束 ===');
  } else if (jsonStartIdx === -1) {
    console.log('[fetch] 未找到 JSON, 打印全部输出:');
    console.log(rawOutput.substring(0, 2000));
    return null;
  }

  const jsonLine = lines[jsonStartIdx].trim();
  console.log('[fetch] JSON长度:', jsonLine.length);

  try {
    const parsed = JSON.parse(jsonLine);

    if (parsed.error) {
      console.log('[fetch] Python 报错:', parsed.error);
    }

    const yfData = parsed?.yfinance || {};
    const bsData = parsed?.baostock || {};
    const yfRecords = yfData.records || [];
    const bsRecords = bsData.records || [];
    const yfMsg = yfData.msg || '';
    const bsMsg = bsData.msg || '';

    console.log(`[fetch] result: Yahoo=${yfRecords.length}条${yfMsg ? ' [' + yfMsg + ']' : ''}  Baostock=${bsRecords.length}条${bsMsg ? ' [' + bsMsg + ']' : ''}`);

    return { yfRecords, bsRecords };
  } catch (e) {
    console.log('[fetch] JSON 解析失败:', e.message);
    console.log('[fetch] 尝试解析的行:', jsonLine.substring(0, 300));
    return null;
  }
}

function ensureCompany(code) {
  console.log(`[fetch] ensureCompany: ${code}`);
  let company = queryOne("SELECT id FROM companies WHERE short_name = ?", [code]);
  if (company) {
    console.log(`[fetch]   已存在 company_id=${company.id}`);
    return company.id;
  }
  run("INSERT INTO companies (name, short_name, status) VALUES (?, ?, 'enabled')", [code, code]);
  company = queryOne("SELECT id FROM companies WHERE short_name = ?", [code]);
  const id = company ? company.id : null;
  console.log(`[fetch]   新建 company_id=${id}`);
  return id;
}

function insertFields(reportId, record) {
  const skipKeys = new Set(['year', 'quarter', 'statDate']);
  let fieldCount = 0;
  for (const [key, val] of Object.entries(record)) {
    if (skipKeys.has(key)) continue;
    const n = parseFloat(val);
    if (isNaN(n)) continue;
    const alias = FIELD_ALIASES[key] || key;
    run("INSERT INTO financial_fields (report_id, source, field_name, field_value, field_alias) VALUES (?, ?, ?, ?, ?)",
      [reportId, 'yfinance', key, Math.round(n * 10) / 10, alias]);
    fieldCount++;
  }
  console.log(`[fetch]   report_id=${reportId}: 写入 ${fieldCount} 字段`);
}

router.post('/', async (_req, res) => {
  const { code } = _req.body;
  if (!code) {
    return res.json({ code: 1, message: '请输入股票代码' });
  }

  console.log('========== [fetch] 开始: ' + code + ' ==========');

  const data = fetchViaPython(code);

  if (!data || !data.yfRecords || data.yfRecords.length === 0) {
    const bsCount = (data && data.bsRecords) ? data.bsRecords.length : 0;
    console.log(`[fetch] 结果: Yahoo=0 Baostock=${bsCount} 不存储`);
    return res.json({
      code: 1,
      message: `Yahoo 无数据  Baostock ${bsCount} 条(仅对比不存储)`,
      data: { yahoo: 0, baostock: bsCount, inserted: 0, skipped: 0 }
    });
  }

  const { yfRecords, bsRecords } = data;

  try {
    const companyId = ensureCompany(code);
    if (!companyId) {
      return res.json({ code: 1, message: '创建公司失败' });
    }

    let inserted = 0;
    let skipped = 0;

    console.log(`[fetch] 开始入库 ${yfRecords.length} 条 Yahoo 数据...`);
    for (const r of yfRecords) {
      const year = r.year;
      const quarter = r.quarter;
      if (!year || !quarter) {
        console.log(`[fetch] 跳过无效记录: year=${year} quarter=${quarter}`);
        continue;
      }

      console.log(`[fetch] 处理 ${year}Q${quarter}...`);
      const existing = queryOne(
        "SELECT id FROM financial_reports WHERE company_id = ? AND year = ? AND quarter = ?",
        [companyId, year, quarter]
      );
      if (existing) {
        console.log(`[fetch]   ${year}Q${quarter} 已存在(id=${existing.id})，跳过`);
        skipped++;
        continue;
      }

      run("INSERT INTO financial_reports (company_id, year, quarter) VALUES (?, ?, ?)",
        [companyId, year, quarter]);

      const report = queryOne(
        "SELECT id FROM financial_reports WHERE company_id = ? AND year = ? AND quarter = ?",
        [companyId, year, quarter]
      );
      if (!report) {
        console.log(`[fetch]   ${year}Q${quarter} 插入失败`);
        continue;
      }

      insertFields(report.id, r);
      inserted++;
    }

    console.log(`[fetch] 入库完成: 新增=${inserted} 跳过=${skipped} Baostock对比=${bsRecords.length}`);
    console.log('========== [fetch] 完成 ==========');

    res.json({
      code: 0,
      message: `Yahoo ${yfRecords.length}条  Baostock ${bsRecords.length}条  新增 ${inserted}条  跳过 ${skipped}条`,
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