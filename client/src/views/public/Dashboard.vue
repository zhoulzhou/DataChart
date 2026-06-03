<script setup>
import { ref, onMounted, computed } from 'vue'
import { getPublicCompanies } from '../../api/companies'
import { getPublicFinancials } from '../../api/financials'
import MetricBarChart from '../../components/MetricBarChart.vue'

const companies = ref([])
const selectedCompany = ref('')
const selectedYear = ref('all')
const financials = ref([])
const viewType = ref('quarterly')
const loading = ref(false)

const years = computed(() => {
  const current = new Date().getFullYear()
  return Array.from({ length: 10 }, (_, i) => current - 5 + i)
})

const isQuarterly = computed(() => viewType.value === 'quarterly')
const isAllYears = computed(() => selectedYear.value === 'all')

const labels = computed(() => {
  const result = (() => {
    if (isQuarterly.value) {
      return financials.value.map(d => String(d.year).slice(-2) + 'Q' + d.quarter)
    }
    if (isAllYears.value) {
      return financials.value.map(d => String(d.year).slice(-2) + '/' + String(d.month).padStart(2, '0'))
    }
    return financials.value.map(d => d.month + '月')
  })()
  console.log('[Dashboard] labels 计算完成, 长度:', result.length, '前3:', result.slice(0, 3))
  return result
})

function makeData(key) {
  return computed(() => financials.value.map(d => d[key] || 0))
}

const revenue = makeData('revenue')
const operatingCost = makeData('operating_cost')
const grossProfit = makeData('gross_profit')
const netProfit = makeData('net_profit')
const cashFlow = makeData('operating_cash_flow')
const inventory = makeData('inventory')
const receivable = makeData('accounts_receivable')
const cashTotal = makeData('cash_total')
const contractLiabilities = makeData('contract_liabilities')
const shortTermLoans = makeData('short_term_loans')
const longTermLoans = makeData('long_term_loans')
const interestExpense = makeData('interest_expense')
const grossMargin = makeData('gross_margin')
const netMargin = makeData('net_margin')
const inventoryTurnoverDays = makeData('inventory_turnover_days')
const arTurnoverDays = makeData('ar_turnover_days')

function makeGrowthData(key, mode = 'yoy') {
  return computed(() => {
    const records = financials.value
    const rates = []
    for (let i = 0; i < records.length; i++) {
      const curr = records[i]
      if (curr[key] == null) {
        rates.push(null)
        continue
      }
      let prev = null
      if (mode === 'qoq') {
        if (isQuarterly.value) {
          const prevQ = curr.quarter > 1 ? curr.quarter - 1 : 4
          const prevY = curr.quarter > 1 ? curr.year : curr.year - 1
          prev = records.find(d => d.year === prevY && d.quarter === prevQ)
        } else {
          const prevM = curr.month > 1 ? curr.month - 1 : 12
          const prevY = curr.month > 1 ? curr.year : curr.year - 1
          prev = records.find(d => d.year === prevY && d.month === prevM)
        }
      } else {
        if (isQuarterly.value) {
          prev = records.find(d => d.year === curr.year - 1 && d.quarter === curr.quarter)
        } else {
          prev = records.find(d => d.year === curr.year - 1 && d.month === curr.month)
        }
      }
      const prevVal = prev ? prev[key] : null
      if (prevVal != null && prevVal !== 0) {
        rates.push(((curr[key] - prevVal) / prevVal) * 100)
      } else {
        rates.push(null)
      }
    }
    return rates
  })
}

const revenueGrowth = makeGrowthData('revenue')
const operatingCostGrowth = makeGrowthData('operating_cost')
const grossProfitGrowth = makeGrowthData('gross_profit')
const netProfitGrowth = makeGrowthData('net_profit')
const cashFlowGrowth = makeGrowthData('operating_cash_flow')
const inventoryGrowth = makeGrowthData('inventory')
const receivableGrowth = makeGrowthData('accounts_receivable')
const cashTotalGrowth = makeGrowthData('cash_total')
const contractLiabilitiesGrowth = makeGrowthData('contract_liabilities')
const shortTermLoansGrowth = makeGrowthData('short_term_loans', 'qoq')
const longTermLoansGrowth = makeGrowthData('long_term_loans')
const interestExpenseGrowth = makeGrowthData('interest_expense', 'qoq')
const grossMarginGrowth = makeGrowthData('gross_margin')
const netMarginGrowth = makeGrowthData('net_margin')
const inventoryTurnoverDaysGrowth = makeGrowthData('inventory_turnover_days')
const arTurnoverDaysGrowth = makeGrowthData('ar_turnover_days')

const periodWord = computed(() => isQuarterly.value ? '季度' : '月度')

const yMax = computed(() => {
  const arr = revenue.value
  if (!arr || arr.length === 0) return undefined
  return Math.max(...arr) * 1.1 || undefined
})

const AMOUNT_METRICS = new Set(['revenue', 'operating_cost', 'gross_profit', 'net_profit',
  'operating_cash_flow', 'cash_total', 'inventory', 'accounts_receivable', 'contract_liabilities',
  'short_term_loans', 'long_term_loans', 'interest_expense'])

function getYMax(key) {
  return AMOUNT_METRICS.has(key) ? yMax.value : undefined
}

const metrics = computed(() => [
  { title: '营业收入', key: 'revenue', color: '#4361ee', data: revenue, growth: revenueGrowth, growthLabel: '同比增速' },
  { title: '营业成本', key: 'operating_cost', color: '#f72585', data: operatingCost, growth: operatingCostGrowth, growthLabel: '同比增速' },
  { title: '毛利', key: 'gross_profit', color: '#2ec4b6', data: grossProfit, growth: grossProfitGrowth, growthLabel: '同比增速' },
  { title: '归母净利润', key: 'net_profit', color: '#7209b7', data: netProfit, growth: netProfitGrowth, growthLabel: '同比增速' },
  { title: '经营现金流净额', key: 'operating_cash_flow', color: '#f8961e', data: cashFlow, growth: cashFlowGrowth, growthLabel: '同比增速' },
  { title: '现金总额', key: 'cash_total', color: '#06d6a0', data: cashTotal, growth: cashTotalGrowth, growthLabel: '同比增速' },
  { title: '存货', key: 'inventory', color: '#4cc9f0', data: inventory, growth: inventoryGrowth, growthLabel: '同比增速' },
  { title: '应收账款', key: 'accounts_receivable', color: '#e63946', data: receivable, growth: receivableGrowth, growthLabel: '同比增速' },
  { title: '合同负债', key: 'contract_liabilities', color: '#ffd166', data: contractLiabilities, growth: contractLiabilitiesGrowth, growthLabel: '同比增速' },
  { title: '短期借款', key: 'short_term_loans', color: '#ef476f', data: shortTermLoans, growth: shortTermLoansGrowth, growthLabel: '环比增速' },
  { title: '长期借款', key: 'long_term_loans', color: '#118ab2', data: longTermLoans, growth: longTermLoansGrowth, growthLabel: '同比增速' },
  { title: '利息支出', key: 'interest_expense', color: '#073b4c', data: interestExpense, growth: interestExpenseGrowth, growthLabel: '环比增速' },
  { title: '毛利率(%)', key: 'gross_margin', color: '#2ecc71', data: grossMargin, growth: grossMarginGrowth, growthLabel: '同比增速' },
  { title: '净利率(%)', key: 'net_margin', color: '#9b59b6', data: netMargin, growth: netMarginGrowth, growthLabel: '同比增速' },
  { title: '存货周转天数', key: 'inventory_turnover_days', color: '#e67e22', data: inventoryTurnoverDays, growth: inventoryTurnoverDaysGrowth, growthLabel: '同比增速' },
  { title: '应收账款周转天数', key: 'ar_turnover_days', color: '#1abc9c', data: arTurnoverDays, growth: arTurnoverDaysGrowth, growthLabel: '同比增速' }
])

async function loadCompanies() {
  const res = await getPublicCompanies()
  if (res.code === 0) {
    companies.value = res.data
  }
}

async function loadData() {
  if (!selectedCompany.value) {
    console.log('[Dashboard] loadData: 未选择公司, 跳过')
    return
  }
  loading.value = true
  const params = {
    company_id: selectedCompany.value,
    period_type: viewType.value
  }
  if (!isAllYears.value) {
    params.year = selectedYear.value
  } else {
    params.year = 'all'
  }
  console.log('[Dashboard] loadData 请求参数:', JSON.stringify(params))
  const res = await getPublicFinancials(params)
  console.log('[Dashboard] API 响应 code:', res.code)
  console.log('[Dashboard] API 响应 data:', res.data)
  if (res.code === 0) {
    financials.value = res.data.records || []
    console.log('[Dashboard] 获取到 financials 记录数:', financials.value.length)
    if (financials.value.length > 0) {
      console.log('[Dashboard] 首条记录样例:', JSON.stringify(financials.value[0]))
      console.log('[Dashboard] 末条记录样例:', JSON.stringify(financials.value[financials.value.length - 1]))
    }
  } else {
    console.log('[Dashboard] API 返回错误:', res.message)
    financials.value = []
  }
  loading.value = false
  console.log('[Dashboard] loadData 完成, loading:', loading.value, 'financials长度:', financials.value.length)
}

function switchView(type) {
  viewType.value = type
  loadData()
}

onMounted(async () => {
  await loadCompanies()
  loadData()
})
</script>

<template>
  <div class="page-container">
    <div style="display:flex;gap:16px;align-items:flex-end;margin-bottom:24px;flex-wrap:wrap;">
      <div class="form-group" style="margin-bottom:0;min-width:220px;">
        <label class="form-label">选择公司</label>
        <select class="form-select" v-model="selectedCompany" @change="loadData()">
          <option value="">请选择公司</option>
          <option v-for="c in companies" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="form-group" style="margin-bottom:0;min-width:140px;">
        <label class="form-label">选择年份</label>
        <select class="form-select" v-model="selectedYear" @change="loadData()">
          <option value="all">全部年度</option>
          <option v-for="y in years" :key="y" :value="y">{{ y }}年</option>
        </select>
      </div>
      <div class="form-group" style="margin-bottom:0;">
        <label class="form-label">查看方式</label>
        <div style="display:flex;gap:0;">
          <button class="btn" :class="viewType === 'monthly' ? 'btn-primary' : 'btn-outline'" style="border-radius:6px 0 0 6px;" @click="switchView('monthly')">月度</button>
          <button class="btn" :class="viewType === 'quarterly' ? 'btn-primary' : 'btn-outline'" style="border-radius:0 6px 6px 0;" @click="switchView('quarterly')">季度</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="empty-state">加载中...</div>

    <template v-else-if="financials.length > 0">
      <div class="charts-grid">
        <div class="chart-box card" v-for="m in metrics" :key="m.key">
          <h3 style="font-size:15px;margin-bottom:12px;">{{ m.title }}</h3>
          <MetricBarChart :title="m.title" :labels="labels" :data="m.data.value" :color="m.color" :y-max="getYMax(m.key)" :growth-data="m.growth?.value" :growth-label="m.growthLabel || '同比增速'" />
        </div>
      </div>
    </template>

    <div v-else-if="selectedCompany" class="empty-state">
      暂无{{ selectedYear === 'all' ? '' : ' ' + selectedYear + ' 年' }}{{ periodWord }}数据，请先在后台录入数据。
    </div>
    <div v-else class="empty-state">
      请先选择一个公司。
    </div>
  </div>
</template>

<style scoped>
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 18px;
}

@media (max-width: 1200px) {
  .charts-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 768px) {
  .charts-grid { grid-template-columns: 1fr; }
}
</style>
