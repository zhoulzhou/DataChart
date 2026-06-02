const express = require('express');
const { execFile } = require('child_process');
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
  '经营活动现金流净额': '经营活动现金流净额(亿)',
  '合同负债': '合同负债(亿)',
  '股东权益': '股东权益(亿)',
  '短期借款': '短期借款(亿)',
  '长期借款': '长期借款(亿)',
  '一年内到期的非流动负债': '一年内到期的非流动负债(亿)',
  '应付债券': '应付债券(亿)',
  '利息支出': '利息支出(亿)'
};

function fetchViaPython(code, startYear, endYear) {
  if (!fs.existsSync(PY_SCRIPT)) {
    console.log('[fetch] FATAL: Python 脚本不存在:', PY_SCRIPT);
    return Promise.resolve(null);
  }
  const args = [PY_SCRIPT, code, String(startYear), String(endYear)];
  const tryCommands = process.platform === 'win32' ? ['python3', 'python'] : ['python3', 'python'];
  return tryExecPython(tryCommands, 0, args);
}

function tryExecPython(commands, idx, args) {
  if (idx >= commands.length) {
    console.log('[fetch] FATAL: Python 完全无输出');
    return Promise.resolve(null);
  }
  const cmd = commands[idx];
  return new Promise((resolve) => {
    console.log(`[fetch] ====== 执行 Python (${idx + 1}/${commands.length}) ======`);
    console.log(`[fetch] CMD: ${cmd} "${args[0]}" ${args.slice(1).join(' ')}`);
    execFile(cmd, args, {
      timeout: 180000,
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    }, (error, stdout, stderr) => {
      if (error) {
        console.log(`[fetch] "${cmd}" 进程退出码:`, error.code);
        console.log(`[fetch] 错误摘要:`, error.message ? error.message.substring(0, 200) : 'none');
        if (error.code === 'ENOENT' || (error.code && error.code >= 9000)) {
          console.log(`[fetch] 命令 ${cmd} 不存在, 尝试下一个`);
          return resolve(tryExecPython(commands, idx + 1, args));
        }
        if (stdout) {
          console.log('[fetch] === Python 部分输出 ===');
          console.log(stdout.substring(0, 3000));
          console.log('[fetch] === 输出结束 ===');
          return resolve(parseOutput(stdout));
        }
        return resolve(tryExecPython(commands, idx + 1, args));
      }
      if (stderr) {
        const debugLines = stderr.trim().split('\n');
        for (const l of debugLines) {
          if (l.trim()) console.log('[py] ' + l.trim());
        }
      }
      console.log(`[fetch] "${cmd}" 进程退出码: 0`);
      resolve(parseOutput(stdout));
    });
  });
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
    if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
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

    if (!Array.isArray(parsed)) {
      if (parsed.error) {
        console.log('[fetch] Python 报错:', parsed.error);
      }
      console.log('[fetch] 非数组 JSON:', typeof parsed);
      return null;
    }

    console.log(`[fetch] 解析: ${parsed.length}条记录`);
    return parsed;
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
  const skipKeys = new Set(['year', 'quarter', 'statDate', 'source']);
  let fieldCount = 0;
  const source = record.source || 'akshare';
  for (const [key, val] of Object.entries(record)) {
    if (skipKeys.has(key)) continue;
    const n = parseFloat(val);
    if (isNaN(n)) continue;
    const alias = FIELD_ALIASES[key] || key;
    const rounded = Math.round(n * 10) / 10;
    run(
      "INSERT INTO financial_fields (report_id, source, field_name, field_value, field_alias) VALUES (?, ?, ?, ?, ?)",
      [reportId, source, key, rounded, alias]
    );
    fieldCount++;
  }
  return fieldCount;
}

router.post('/', async (_req, res) => {
  const { code, start_year, end_year } = _req.body;
  if (!code) {
    return res.json({ code: 1, message: '请输入股票代码' });
  }

  const startY = start_year || 2024;
  const endY = end_year || new Date().getFullYear();

  console.log('========== [fetch] 开始: ' + code + ` (${startY}-${endY})` + ' ==========');

  const records = await fetchViaPython(code, startY, endY);

  if (!records || records.length === 0) {
    console.log('[fetch] 无数据');
    return res.json({
      code: 1,
      message: '未获取到数据',
      data: { inserted: 0, skipped: 0, total: 0 }
    });
  }

  try {
    const companyId = ensureCompany(code);
    if (!companyId) {
      return res.json({ code: 1, message: '创建公司失败' });
    }

    let inserted = 0;
    let skipped = 0;
    let yfSkipped = 0;

    console.log(`[fetch] 开始入库 ${records.length} 条数据...`);
    for (const r of records) {
      if (r.source === 'yfinance') {
        console.log(`[fetch] 跳过 yfinance 数据 ${r.year}Q${r.quarter} (数据不全不存储)`);
        yfSkipped++;
        continue;
      }
      const year = r.year;
      const quarter = r.quarter;
      if (!year || !quarter) {
        console.log('[fetch] 跳过无效记录:', JSON.stringify(r));
        continue;
      }

      console.log(`[fetch] 处理 ${year}Q${quarter} (来源:${r.source})...`);
      const existing = queryOne(
        "SELECT id FROM financial_reports WHERE company_id = ? AND year = ? AND quarter = ?",
        [companyId, year, quarter]
      );
      if (existing) {
        console.log(`[fetch]   ${year}Q${quarter} 已存在(id=${existing.id})，跳过`);
        skipped++;
        continue;
      }

      run(
        "INSERT INTO financial_reports (company_id, year, quarter) VALUES (?, ?, ?)",
        [companyId, year, quarter]
      );

      const report = queryOne(
        "SELECT id FROM financial_reports WHERE company_id = ? AND year = ? AND quarter = ?",
        [companyId, year, quarter]
      );
      if (!report) {
        console.log(`[fetch]   ${year}Q${quarter} 插入失败`);
        continue;
      }

      const count = insertFields(report.id, r);
      console.log(`[fetch]   report_id=${report.id}: 写入 ${count} 字段`);
      inserted++;
    }

    console.log(`[fetch] 入库完成: 新增=${inserted} 跳过=${skipped} yfinance跳过=${yfSkipped}`);
    console.log('========== [fetch] 完成 ==========');

    if (inserted === 0 && yfSkipped > 0) {
      return res.json({
        code: 1,
        message: `yfinance数据不全不存储(${yfSkipped}条已跳过)`,
        data: { inserted: 0, skipped, total: records.length, yfSkipped }
      });
    }

    res.json({
      code: 0,
      message: `共${records.length}条  新增${inserted}条  跳过${skipped}条${yfSkipped > 0 ? '  yfinance' + yfSkipped + '条未存储' : ''}`,
      data: { inserted, skipped, total: records.length, yfSkipped }
    });
  } catch (err) {
    console.log('[fetch] 入库异常:', err.stack || err.message);
    res.json({ code: 1, message: '入库失败: ' + err.message });
  }
});

module.exports = router;