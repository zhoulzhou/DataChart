<script setup>
import { ref, onMounted } from 'vue'
import { getCompanies, createCompany, updateCompany, updateCompanyStatus, deleteCompany } from '../../api/companies'

const companies = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ name: '', short_name: '' })
const message = ref('')

async function loadCompanies() {
  const res = await getCompanies()
  if (res.code === 0) companies.value = res.data
}

function openAdd() {
  editing.value = null
  form.value = { name: '', short_name: '' }
  showModal.value = true
}

function openEdit(company) {
  editing.value = company
  form.value = { name: company.name, short_name: company.short_name }
  showModal.value = true
}

async function handleSave() {
  if (!form.value.name || !form.value.short_name) {
    message.value = '名称和简称不能为空'
    return
  }
  let res
  if (editing.value) {
    res = await updateCompany(editing.value.id, form.value)
  } else {
    res = await createCompany(form.value)
  }
  if (res.code === 0) {
    showModal.value = false
    message.value = res.message
    loadCompanies()
  } else {
    message.value = res.message
  }
}

async function toggleStatus(company) {
  const newStatus = company.status === 'enabled' ? 'disabled' : 'enabled'
  const res = await updateCompanyStatus(company.id, newStatus)
  if (res.code === 0) {
    message.value = res.message
    loadCompanies()
  } else {
    message.value = res.message
  }
}

async function handleDelete(company) {
  if (!confirm(`确定删除公司"${company.name}"吗？\n注意：存在财务数据时无法删除。`)) return
  const res = await deleteCompany(company.id)
  if (res.code === 0) {
    message.value = res.message
    loadCompanies()
  } else {
    message.value = res.message
  }
}

onMounted(loadCompanies)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">公司管理</h1>
      <button class="btn btn-primary" @click="openAdd">新增公司</button>
    </div>
    <div v-if="message" class="alert" :class="message.includes('成功') ? 'alert-success' : 'alert-error'">{{ message }}</div>
    <table>
      <thead>
        <tr>
          <th>公司全称</th>
          <th>公司简称（ID）</th>
          <th>状态</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in companies" :key="c.id">
          <td>{{ c.name }}</td>
          <td><code style="background:#f5f5f5;padding:2px 6px;border-radius:3px;">{{ c.short_name }}</code></td>
          <td>
            <span :style="{color: c.status === 'enabled' ? '#2ec4b6' : '#e63946'}">
              {{ c.status === 'enabled' ? '启用' : '停用' }}
            </span>
          </td>
          <td>{{ c.created_at }}</td>
          <td>
            <button class="btn btn-sm btn-outline" @click="openEdit(c)">编辑</button>
            <button class="btn btn-sm" :class="c.status === 'enabled' ? 'btn-danger' : 'btn-success'" style="margin-left:6px;" @click="toggleStatus(c)">
              {{ c.status === 'enabled' ? '停用' : '启用' }}
            </button>
            <button class="btn btn-sm btn-danger" style="margin-left:6px;" @click="handleDelete(c)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h3 class="modal-title">{{ editing ? '编辑公司' : '新增公司' }}</h3>
        <div class="form-group">
          <label class="form-label">公司全称</label>
          <input class="form-input" v-model="form.name" placeholder="请输入公司全称" />
        </div>
        <div class="form-group">
          <label class="form-label">公司简称（唯一ID）</label>
          <input class="form-input" v-model="form.short_name" placeholder="请输入唯一简称" />
        </div>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showModal = false">取消</button>
          <button class="btn btn-primary" @click="handleSave">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>
