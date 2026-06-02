<script setup>
import { ref, onMounted, computed } from 'vue'
import { getCompanies } from '../../api/companies'
import { getFinancials, updateFinancial, deleteFinancial } from '../../api/financials'

const companies = ref([])
const records = ref([])
const filters = ref({ company_id: '', year: '', month: '', quarter: '', period_type: '' })
const message = ref({ type: '', text: '' })
const showEdit = ref(false)
const editing = ref(null)
const editForm = ref({})
const hasSearched = ref(false)

const page = ref(1)
const pageSize = 15
const years = Array.from({ length: 10 }, (_, i) => new Date().getFullYear() - 5 + i)

const totalPages = computed(() => Math.ceil(records.value.length / pageSize) || 1)
const pagedRecords = computed(() => {
  const start = (page.value - 1) * pageSize
  return records.value.slice(start, start + pageSize)
})

async function loadCompanies() {
  const res = await getCompanies({ status: 'enabled' })
  if (res.code === 0) companies.value = res.data
}

async function loadData() {
  hasSearched.value = true
  const params = {}
  if (filters.value.company_id) params.company_id = filters.value.company_id
  if (filters.value.year) params.year = filters.value.year
  if (filters.value.month) params.month = filters.value.month
  if (filters.value.quarter) params.quarter = filters.value.quarter
  if (filters.value.period_type) params.period_type = filters.value.period_type
  const res = await getFinancials(params)
  if (res.code === 0) records.value = res.data
}

function periodLabel(r) {
  if (r.quarter != null) return 'Q' + r.quarter
  if (r.month != null) return r.month + '月'
  return '-'
}

function periodTitle(r) {
  if (r.quarter != null) return r.year + '年 Q' + r.quarter
  if (r.month != null) return r.year + '年' + r.month + '月'
  return r.year + '年'
}

const isEditingQuarterly = computed(() => editing.value?.quarter != null)

function openEdit(record) {
  editing.value = record
  editForm.value = {
    year: record.year,
    month: record.month,
    quarter: record.quarter,
    revenue: record.revenue, operating_cost: record.operating_cost,
    gross_profit: record.gross_profit, net_profit: record.net_profit,
    operating_cash_flow: record.operating_cash_flow, inventory: record.inventory,
    accounts_receivable: record.accounts_receivable,
    cash_total: record.cash_total, contract_liabilities: record.contract_liabilities,
    short_term_loans: record.short_term_loans, long_term_loans: record.long_term_loans,
    interest_expense: record.interest_expense
  }
  showEdit.value = true
}

async function handleUpdate() {
  const res = await updateFinancial(editing.value.id, editForm.value)
  if (res.code === 0) {
    showEdit.value = false
    message.value = { type: 'success', text: '修改成功' }
    loadData()
  } else {
    message.value = { type: 'error', text: res.message }
  }
}

async function handleDelete(record) {
  if (!confirm(`确定删除 ${record.company_name} ${periodTitle(record)} 的数据吗？`)) return
  const res = await deleteFinancial(record.id)
  if (res.code === 0) {
    message.value = { type: 'success', text: '删除成功' }
    loadData()
  } else {
    message.value = { type: 'error', text: res.message }
  }
}

function formatNum(v) {
  if (v == null) return '-'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function search() {
  page.value = 1
  loadData()
}

onMounted(() => {
  loadCompanies()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">财务数据列表</h1>
    </div>
    <div v-if="message.text" :class="message.type === 'error' ? 'alert alert-error' : 'alert alert-success'">{{ message.text }}</div>
    <div class="filters">
      <div class="form-group">
        <label class="form-label">公司</label>
        <select class="form-select" v-model="filters.company_id" style="min-width:160px;">
          <option value="">全部公司</option>
          <option v-for="c in companies" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">年份</label>
        <select class="form-select" v-model="filters.year" style="min-width:120px;">
          <option value="">全部年份</option>
          <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">类型</label>
        <select class="form-select" v-model="filters.period_type" style="min-width:110px;">
          <option value="">全部类型</option>
          <option value="monthly">月度</option>
          <option value="quarterly">季度</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">月份</label>
        <select class="form-select" v-model="filters.month" style="min-width:100px;">
          <option value="">全部月份</option>
          <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">季度</label>
        <select class="form-select" v-model="filters.quarter" style="min-width:100px;">
          <option value="">全部季度</option>
          <option :value="1">Q1</option>
          <option :value="2">Q2</option>
          <option :value="3">Q3</option>
          <option :value="4">Q4</option>
        </select>
      </div>
      <div class="form-group" style="display:flex;align-items:flex-end;">
        <button class="btn btn-primary" @click="search">查询</button>
      </div>
    </div>

    <table v-if="hasSearched">
      <thead>
        <tr>
          <th>公司</th>
          <th>年份</th>
          <th>期间</th>
          <th>营业收入</th>
          <th>营业成本</th>
          <th>毛利</th>
          <th>净利</th>
          <th>经营现金流净额</th>
          <th>存货</th>
          <th>应收账款</th>
          <th>现金总额</th>
          <th>合同负债</th>
          <th>短期借款</th>
          <th>长期借款</th>
          <th>利息支出</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in pagedRecords" :key="r.id">
          <td>{{ r.company_name }}</td>
          <td>{{ r.year }}</td>
          <td>{{ periodLabel(r) }}</td>
          <td>{{ formatNum(r.revenue) }}</td>
          <td>{{ formatNum(r.operating_cost) }}</td>
          <td>{{ formatNum(r.gross_profit) }}</td>
          <td>{{ formatNum(r.net_profit) }}</td>
          <td>{{ formatNum(r.operating_cash_flow) }}</td>
          <td>{{ formatNum(r.inventory) }}</td>
          <td>{{ formatNum(r.accounts_receivable) }}</td>
          <td>{{ formatNum(r.cash_total) }}</td>
          <td>{{ formatNum(r.contract_liabilities) }}</td>
          <td>{{ formatNum(r.short_term_loans) }}</td>
          <td>{{ formatNum(r.long_term_loans) }}</td>
          <td>{{ formatNum(r.interest_expense) }}</td>
          <td>
            <button class="btn btn-sm btn-outline" @click="openEdit(r)">编辑</button>
            <button class="btn btn-sm btn-danger" style="margin-left:6px;" @click="handleDelete(r)">删除</button>
          </td>
        </tr>
        <tr v-if="records.length === 0">
          <td colspan="15" style="text-align:center;color:#999;padding:40px;">暂无数据</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty-state" style="padding:80px 20px;font-size:16px;">
      请选择筛选条件后点击"查询"按钮
    </div>

    <div class="pagination" v-if="totalPages > 1">
      <button :disabled="page === 1" @click="page = 1">首页</button>
      <button :disabled="page === 1" @click="page--">上一页</button>
      <button v-for="p in totalPages" :key="p" :class="{ active: p === page }" @click="page = p">{{ p }}</button>
      <button :disabled="page === totalPages" @click="page++">下一页</button>
      <button :disabled="page === totalPages" @click="page = totalPages">末页</button>
    </div>

    <div v-if="showEdit" class="modal-overlay" @click.self="showEdit = false">
      <div class="modal" style="max-width:700px;">
        <h3 class="modal-title">编辑数据 — {{ editing.company_name }} {{ periodTitle(editing) }}</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px;">
          <div class="form-group">
            <label class="form-label">年份</label>
            <input class="form-input no-spin" type="number" v-model.number="editForm.year" min="2000" max="2100" />
          </div>
          <div class="form-group">
            <label class="form-label">季度</label>
            <select class="form-select" v-model.number="editForm.quarter" :disabled="!isEditingQuarterly">
              <option :value="1">Q1</option>
              <option :value="2">Q2</option>
              <option :value="3">Q3</option>
              <option :value="4">Q4</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">月份</label>
            <select class="form-select" v-model.number="editForm.month" :disabled="isEditingQuarterly">
              <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
            </select>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
          <div class="form-group"><label class="form-label">营业收入</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.revenue" /></div>
          <div class="form-group"><label class="form-label">营业成本</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.operating_cost" /></div>
          <div class="form-group"><label class="form-label">毛利</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.gross_profit" /></div>
          <div class="form-group"><label class="form-label">净利</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.net_profit" /></div>
          <div class="form-group"><label class="form-label">经营现金流净额</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.operating_cash_flow" /></div>
          <div class="form-group"><label class="form-label">存货</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.inventory" /></div>
          <div class="form-group"><label class="form-label">应收账款</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.accounts_receivable" /></div>
          <div class="form-group"><label class="form-label">现金总额</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.cash_total" /></div>
          <div class="form-group"><label class="form-label">合同负债</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.contract_liabilities" /></div>
          <div class="form-group"><label class="form-label">短期借款</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.short_term_loans" /></div>
          <div class="form-group"><label class="form-label">长期借款</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.long_term_loans" /></div>
          <div class="form-group"><label class="form-label">利息支出</label><input class="form-input no-spin" type="number" step="any" v-model="editForm.interest_expense" /></div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showEdit = false">取消</button>
          <button class="btn btn-primary" @click="handleUpdate">保存修改</button>
        </div>
      </div>
    </div>
  </div>
</template>
