const express = require('express')
const https = require('https')
const http = require('http')
const { queryAll, queryOne, run } = require('../db')
const { authMiddleware } = require('../middleware/auth')

const router = express.Router()
router.use(authMiddleware)

function httpGet(url) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http
    mod.get(url, (res) => {
      let data = ''
      res.on('data', chunk => data += chunk)
      res.on('end', () => resolve(data))
    }).on('error', reject)
  })
}

function parseQuarter(dateStr) {
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

  try {
    const raw = await httpGet(
      `http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get_cwgx.php?type=Q&token=70f12f2f4f091e4e90272a310c76c5e&st=${code}&sr=&p=1&ps=200`
    )

    const arr = JSON.parse(raw)
    if (!Array.isArray(arr) || arr.length === 0) {
      return res.json({ code: 1, message: '未获取到数据，请检查股票代码是否正确' })
    }

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

      if (!year || !quarter) continue

      const existing = queryOne(
        "SELECT id FROM financial_data WHERE company_id = ? AND year = ? AND quarter = ?",
        [companyId, year, quarter]
      )
      if (existing) {
        skipped++
        continue
      }

      const revenue = round1(row.businessincome)
      const operatingCost = round1(row.cost)
      const grossProfit = round1(revenue - operatingCost)
      const netProfit = round1(row.netprofit)
      const operatingCashFlow = round1(row.operatecashflow)
      const inventory = round1(row.inventory)
      const accountsReceivable = round1(row.receivable)
      const cashTotal = round1((parseFloat(row.moneyfunds) || 0) + (parseFloat(row.tradingasset) || 0))
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

    res.json({
      code: 0,
      message: `获取 ${arr.length} 条，新增 ${inserted} 条，跳过 ${skipped} 条`,
      data: { total: arr.length, inserted, skipped }
    })
  } catch (err) {
    res.json({ code: 1, message: '请求失败: ' + err.message })
  }
})

module.exports = router
