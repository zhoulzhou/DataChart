const express = require('express')
const https = require('https')
const http = require('http')
const { execSync } = require('child_process')
const path = require('path')
const fs = require('fs')
const { queryOne, run } = require('../db')
const { authMiddleware } = require('../middleware/auth')

const router = express.Router()
router.use(authMiddleware)

const PY_SCRIPT = path.join(__dirname, '..', 'getData.py')
const EASTMONEY_URL = 'https://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get_cwgx.php'

function httpGetJSON(url) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url)
    const mod = parsed.protocol === 'https:' ? https : http
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
    }

    console.log('[fetch] 请求东方财富:', url)

    const req = mod.request(options, (res) => {
      console.log('[fetch] 响应状态码:', res.statusCode)
      let data = ''
      res.on('data', chunk => data += chunk)
      res.on('end', () => {
        console.log('[fetch] 响应长度:', data.length, '前200字符:', data.substring(0, 200))
        if (res.statusCode >= 400) {
          return reject(new Error('HTTP ' + res.statusCode))
        }
        try {
          resolve(JSON.parse(data))
        } catch (e) {
          reject(new Error('JSON解析失败: ' + data.substring(0, 300)))
        }
      })
    })
    req.on('timeout', () => { req.destroy(); reject(new Error('请求超时(15s)')) })
    req.on('error', (err) => reject(err))
    req.end()
  })
}

function fetchViaPython(code) {
  if (!fs.existsSync(PY_SCRIPT)) {
    console.log('[fetch] Python 脚本不存在:', PY_SCRIPT)
    return null
  }
  try {
    console.log('[fetch] ====== 调用 Python Baostock ======')
    const result = execSync(`python3 ${PY_SCRIPT} ${code}`, {
      timeout: 60000,
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024
    })
    console.log('[fetch] Python 前200字符:', result.substring(0, 200))

    const rows = []
    const lines = result.trim().split('\n')
    for (const line of lines) {
      const parts = line.split('\t')
      if (parts.length < 10) continue
      rows.push({
        reportdate: parts[0],
        businessincome: parseFloat(parts[1]) || 0,
        cost: parseFloat(parts[2]) || 0,
        netprofit: parseFloat(parts[3]) || 0,
        operatecashflow: parseFloat(parts[4]) || 0,
        inventory: parseFloat(parts[5]) || 0,
        receivable: parseFloat(parts[6]) || 0,
        moneyfunds: parseFloat(parts[7]) || 0,
        tradingasset: parseFloat(parts[8]) || 0,
        contractliability: parseFloat(parts[9]) || 0
      })
    }
    return rows.length > 0 ? rows : null
  } catch (e) {
    console.log('[fetch] Python 调用失败:', e.message)
    return null
  }
}

function fetchViaEastmoney(code) {
  return new Promise(async (resolve) => {
    try {
      console.log('[fetch] ====== 尝试东方财富 API ======')
      const arr = await httpGetJSON(
        `${EASTMONEY_URL}?type=Q&token=70f12f2f4f091e4e90272a310c76c5e&st=${code}&sr=&p=1&ps=200`
      )
      if (!Array.isArray(arr) || arr.length === 0) {
        console.log('[fetch] 东方财富返回空或非数组')
        resolve(null)
        return
      }
      const rows = arr.map(row => ({
        reportdate: String(row.reportdate || ''),
        businessincome: parseFloat(row.businessincome) || 0,
        cost: parseFloat(row.cost) || 0,
        netprofit: parseFloat(row.netprofit) || 0,
        operatecashflow: parseFloat(row.operatecashflow) || 0,
        inventory: parseFloat(row.inventory) || 0,
        receivable: parseFloat(row.receivable) || 0,
        moneyfunds: parseFloat(row.moneyfunds) || 0,
        tradingasset: parseFloat(row.tradingasset) || 0,
        contractliability: parseFloat(row.contractliability) || 0
      }))
      console.log('[fetch] 东方财富返回', rows.length, '条')
      resolve(rows)
    } catch (e) {
      console.log('[fetch] 东方财富 API 失败:', e.message)
      resolve(null)
    }
  })
}

function parseQuarter(dateStr) {
  if (!dateStr) return null
  const m = parseInt(dateStr.substring(5, 7))
  if (m === 3) return 1
  if (m === 6) return 2
  if (m === 9) return 3
  if (m === 12) return 4
  return null
}

function round1(v) {
  const n = parseFloat(v)
  if (isNaN(n)) return 0
  return Math.round(n * 10) / 10
}

function ensureCompany(code) {
  let company = queryOne("SELECT id FROM companies WHERE short_name = ?", [code])
  if (company) return company.id
  run("INSERT INTO companies (name, short_name, status) VALUES (?, ?, 'enabled')", [code, code])
  company = queryOne("SELECT id FROM companies WHERE short_name = ?", [code])
  return company ? company.id : null
}

router.post('/', async (_req, res) => {
  const { code } = _req.body
  if (!code) {
    return res.json({ code: 1, message: '请输入股票代码' })
  }

  console.log('========== [fetch] 开始获取股票:', code, '==========')

  let arr = null
  let source = ''

  arr = fetchViaPython(code)
  if (arr && arr.length > 0) {
    source = 'Baostock'
  } else {
    arr = await fetchViaEastmoney(code)
    if (arr && arr.length > 0) {
      source = '东方财富'
    }
  }

  if (!arr || arr.length === 0) {
    console.log('[fetch] 所有数据源均失败')
    return res.json({ code: 1, message: '未获取到数据：Baostock和东方财富均无返回，请确认股票代码正确且网络可达' })
  }

  try {
    const companyId = ensureCompany(code)
    if (!companyId) {
      return res.json({ code: 1, message: '创建公司失败' })
    }

    let inserted = 0
    let skipped = 0

    for (const row of arr) {
      const dateStr = String(row.reportdate || '')
      const year = parseInt(dateStr.substring(0, 4))
      const quarter = parseQuarter(dateStr)

      if (!year || !quarter) {
        console.log('[fetch] 跳过:', dateStr)
        continue
      }

      const existing = queryOne(
        "SELECT id FROM financial_data WHERE company_id = ? AND year = ? AND quarter = ?",
        [companyId, year, quarter]
      )
      if (existing) { skipped++; continue }

      const revenue = round1(row.businessincome)
      const operatingCost = round1(row.cost)
      const grossProfit = round1(revenue - operatingCost)
      const netProfit = round1(row.netprofit)
      const operatingCashFlow = round1(row.operatecashflow)
      const inventory = round1(row.inventory)
      const accountsReceivable = round1(row.receivable)
      const cashTotal = round1(row.moneyfunds + row.tradingasset)
      const contractLiabilities = round1(row.contractliability)

      run(`
        INSERT INTO financial_data
        (company_id, year, month, quarter, revenue, operating_cost, gross_profit, net_profit,
         operating_cash_flow, inventory, accounts_receivable, cash_total, contract_liabilities)
        VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `, [
        companyId, year, quarter,
        revenue, operatingCost, grossProfit, netProfit,
        operatingCashFlow, inventory, accountsReceivable,
        cashTotal, contractLiabilities
      ])
      inserted++
    }

    console.log('[fetch] 入库完成: 源=' + source + ', 新增=' + inserted + ', 跳过=' + skipped)
    console.log('========== [fetch] 完成 ==========')

    res.json({
      code: 0,
      message: `[${source}] 获取 ${arr.length} 条，新增 ${inserted} 条，跳过 ${skipped} 条`,
      data: { total: arr.length, inserted, skipped, source }
    })
  } catch (err) {
    console.log('[fetch] 入库异常:', err.stack || err.message)
    res.json({ code: 1, message: '入库失败: ' + err.message })
  }
})

module.exports = router