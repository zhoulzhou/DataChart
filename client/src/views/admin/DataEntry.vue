<script setup>
import { ref, onMounted } from 'vue'
import { getCompanies } from '../../api/companies'
import { createFinancial } from '../../api/financials'

const companies = ref([])
const periodType = ref('monthly')
const form = ref({
  company_id: '',
  year: new Date().getFullYear(),
  month: 1,
  quarter: 1,
  revenue: '',
  gross_profit: '',
  net_profit: '',
  operating_cash_flow: '',
  inventory: '',
  accounts_receivable: ''
})
const message = ref({ type: '', text: '' })
const years = Array.from({ length: 10 }, (_, i) => new Date().getFullYear() - 5 + i)

const quarters = [
  { value: 1, label: '第一季度 (1-3月)' },
  { value: 2, label: '第二季度 (4-6月)' },
  { value: 3, label: '第三季度 (7-9月)' },
  { value: 4, label: '第四季度 (10-12月)' }
]

async function loadCompanies() {
  const res = await getCompanies({ status: 'enabled' })
  if (res.code === 0) companies.value = res.data
}

async function handleSave() {
  if (!form.value.company_id) {
    message.value = { type: 'error', text: '请选择公司' }
    return
  }
  const data = {
    ...form.value,
    period_type: periodType.value
  }
  for (const key of ['revenue','gross_profit','net_profit','operating_cash_flow','inventory','accounts_receivable']) {
    data[key] = parseFloat(data[key]) || 0
  }
  const res = await createFinancial(data)
  if (res.code === 0) {
    message.value = { type: 'success', text: '保存成功' }
  } else {
    message.value = { type: 'error', text: res.message }
  }
}

function switchPeriodType() {
  form.value.month = 1
  form.value.quarter = 1
  message.value = { type: '', text: '' }
}

onMounted(loadCompanies)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">财务数据录入</h1>
    </div>
    <div v-if="message.text" :class="message.type === 'error' ? 'alert alert-error' : 'alert alert-success'">{{ message.text }}</div>
    <div class="card" style="max-width:700px;">
      <div style="margin-bottom:16px;">
        <label class="form-label">录入类型</label>
        <div style="display:flex;gap:0;">
          <button
            class="btn"
            :class="periodType === 'monthly' ? 'btn-primary' : 'btn-outline'"
            style="border-radius:6px 0 0 6px;"
            @click="periodType = 'monthly'; switchPeriodType()"
          >月度录入</button>
          <button
            class="btn"
            :class="periodType === 'quarterly' ? 'btn-primary' : 'btn-outline'"
            style="border-radius:0 6px 6px 0;"
            @click="periodType = 'quarterly'; switchPeriodType()"
          >季度录入</button>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
        <div class="form-group">
          <label class="form-label">选择公司</label>
          <select class="form-select" v-model="form.company_id">
            <option value="">请选择公司</option>
            <option v-for="c in companies" :key="c.id" :value="c.id">{{ c.short_name || c.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">年份</label>
          <select class="form-select" v-model="form.year">
            <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
          </select>
        </div>
        <div class="form-group" v-if="periodType === 'monthly'">
          <label class="form-label">月份</label>
          <select class="form-select" v-model="form.month">
            <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
          </select>
        </div>
        <div class="form-group" v-else>
          <label class="form-label">季度</label>
          <select class="form-select" v-model="form.quarter">
            <option v-for="q in quarters" :key="q.value" :value="q.value">{{ q.label }}</option>
          </select>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div class="form-group">
          <label class="form-label">营业收入</label>
          <input class="form-input" type="number" step="0.01" v-model="form.revenue" placeholder="0.00" />
        </div>
        <div class="form-group">
          <label class="form-label">毛利</label>
          <input class="form-input" type="number" step="0.01" v-model="form.gross_profit" placeholder="0.00" />
        </div>
        <div class="form-group">
          <label class="form-label">净利</label>
          <input class="form-input" type="number" step="0.01" v-model="form.net_profit" placeholder="0.00" />
        </div>
        <div class="form-group">
          <label class="form-label">经营现金流</label>
          <input class="form-input" type="number" step="0.01" v-model="form.operating_cash_flow" placeholder="0.00" />
        </div>
        <div class="form-group">
          <label class="form-label">存货</label>
          <input class="form-input" type="number" step="0.01" v-model="form.inventory" placeholder="0.00" />
        </div>
        <div class="form-group">
          <label class="form-label">应收账款</label>
          <input class="form-input" type="number" step="0.01" v-model="form.accounts_receivable" placeholder="0.00" />
        </div>
      </div>
      <div style="margin-top:16px;">
        <button class="btn btn-primary" @click="handleSave">保存数据</button>
      </div>
    </div>
  </div>
</template>
