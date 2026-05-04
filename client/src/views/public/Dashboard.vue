<script setup>
import { ref, onMounted, computed } from 'vue'
import { getPublicCompanies } from '../../api/companies'
import { getPublicFinancials } from '../../api/financials'
import KpiCards from '../../components/KpiCards.vue'
import RevenueNetProfitChart from '../../components/RevenueNetProfitChart.vue'
import RevenueGrossChart from '../../components/RevenueGrossChart.vue'
import InventoryReceivableChart from '../../components/InventoryReceivableChart.vue'
import ProfitRateChart from '../../components/ProfitRateChart.vue'

const companies = ref([])
const selectedCompany = ref('')
const selectedYear = ref(new Date().getFullYear())
const financials = ref([])
const viewType = ref('monthly')
const loading = ref(false)

const years = computed(() => {
  const current = new Date().getFullYear()
  return Array.from({ length: 10 }, (_, i) => current - 5 + i)
})

const isQuarterly = computed(() => viewType.value === 'quarterly')

const labels = computed(() => {
  if (isQuarterly.value) {
    return financials.value.map(d => 'Q' + d.quarter)
  }
  return financials.value.map(d => d.month + '月')
})

const cardsData = computed(() => {
  if (financials.value.length === 0) return {}
  const latest = financials.value[financials.value.length - 1]
  return latest
})

const revenueData = computed(() => financials.value.map(d => d.revenue))
const grossProfitData = computed(() => financials.value.map(d => d.gross_profit))
const netProfitData = computed(() => financials.value.map(d => d.net_profit))
const inventoryData = computed(() => financials.value.map(d => d.inventory))
const receivableData = computed(() => financials.value.map(d => d.accounts_receivable))

const grossRateData = computed(() =>
  financials.value.map(d => d.revenue > 0 ? d.gross_profit / d.revenue : 0)
)
const netRateData = computed(() =>
  financials.value.map(d => d.revenue > 0 ? d.net_profit / d.revenue : 0)
)

const periodWord = computed(() => isQuarterly.value ? '季度' : '月度')

async function loadCompanies() {
  const res = await getPublicCompanies()
  if (res.code === 0) {
    companies.value = res.data
    if (companies.value.length > 0 && !selectedCompany.value) {
      selectedCompany.value = companies.value[0].id
    }
  }
}

async function loadData() {
  if (!selectedCompany.value) return
  loading.value = true
  const res = await getPublicFinancials({
    company_id: selectedCompany.value,
    year: selectedYear.value,
    period_type: viewType.value
  })
  if (res.code === 0) {
    financials.value = res.data.records || []
  } else {
    financials.value = []
  }
  loading.value = false
}

function switchView(type) {
  viewType.value = type
  loadData()
}

function onCompanyChange() {
  loadData()
}

function onYearChange() {
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
      <div class="form-group" style="margin-bottom:0;min-width:200px;">
        <label class="form-label">选择公司</label>
        <select class="form-select" v-model="selectedCompany" @change="onCompanyChange">
          <option value="">请选择公司</option>
          <option v-for="c in companies" :key="c.id" :value="c.id">{{ c.short_name || c.name }}</option>
        </select>
      </div>
      <div class="form-group" style="margin-bottom:0;min-width:140px;">
        <label class="form-label">选择年份</label>
        <select class="form-select" v-model="selectedYear" @change="onYearChange">
          <option v-for="y in years" :key="y" :value="y">{{ y }}年</option>
        </select>
      </div>
      <div class="form-group" style="margin-bottom:0;">
        <label class="form-label">查看方式</label>
        <div style="display:flex;gap:0;">
          <button
            class="btn"
            :class="viewType === 'monthly' ? 'btn-primary' : 'btn-outline'"
            style="border-radius:6px 0 0 6px;"
            @click="switchView('monthly')"
          >月度</button>
          <button
            class="btn"
            :class="viewType === 'quarterly' ? 'btn-primary' : 'btn-outline'"
            style="border-radius:0 6px 6px 0;"
            @click="switchView('quarterly')"
          >季度</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="empty-state">加载中...</div>

    <template v-else-if="financials.length > 0">
      <KpiCards :cards-data="cardsData" />

      <div class="charts-grid">
        <div class="chart-box card">
          <h3 style="font-size:15px;margin-bottom:12px;">营业收入 &amp; 净利 {{ periodWord }}趋势</h3>
          <RevenueNetProfitChart :labels="labels" :revenue-data="revenueData" :net-profit-data="netProfitData" />
        </div>
        <div class="chart-box card">
          <h3 style="font-size:15px;margin-bottom:12px;">营业收入 &amp; 毛利 {{ periodWord }}对比</h3>
          <RevenueGrossChart :labels="labels" :revenue-data="revenueData" :gross-profit-data="grossProfitData" />
        </div>
        <div class="chart-box card">
          <h3 style="font-size:15px;margin-bottom:12px;">存货 &amp; 应收账款 {{ periodWord }}走势</h3>
          <InventoryReceivableChart :labels="labels" :inventory-data="inventoryData" :receivable-data="receivableData" />
        </div>
        <div class="chart-box card">
          <h3 style="font-size:15px;margin-bottom:12px;">毛利率 &amp; 净利率</h3>
          <ProfitRateChart :labels="labels" :gross-rate-data="grossRateData" :net-rate-data="netRateData" />
        </div>
      </div>
    </template>

    <div v-else-if="selectedCompany" class="empty-state">
      暂无 {{ selectedYear }} 年的{{ periodWord }}数据，请先在后台录入数据。
    </div>
    <div v-else class="empty-state">
      请先选择一个公司。
    </div>
  </div>
</template>

<style scoped>
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
