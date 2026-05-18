<script setup>
import { ref, onMounted } from 'vue'
import request from '../../api/request'

const backups = ref([])
const message = ref({ type: '', text: '' })
const loading = ref(false)
const deleting = ref(null)

async function loadList() {
  const res = await request.get('/backup/list')
  if (res.code === 0) {
    backups.value = res.data
  }
}

async function handleBackup() {
  loading.value = true
  message.value = { type: '', text: '' }
  try {
    const res = await request.post('/backup/create')
    if (res.code === 0) {
      message.value = { type: 'success', text: `备份成功 — ${res.data.name}` }
      loadList()
    } else {
      message.value = { type: 'error', text: res.message }
    }
  } catch {
    message.value = { type: 'error', text: '备份请求失败' }
  }
  loading.value = false
}

async function handleDelete(name) {
  if (!confirm(`确认删除备份文件 ${name} ？`)) return
  deleting.value = name
  message.value = { type: '', text: '' }
  try {
    const res = await request.delete(`/backup/${name}`)
    if (res.code === 0) {
      message.value = { type: 'success', text: `已删除 ${name}` }
      loadList()
    } else {
      message.value = { type: 'error', text: res.message }
    }
  } catch {
    message.value = { type: 'error', text: '删除请求失败' }
  }
  deleting.value = null
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">数据库备份</h1>
    </div>

    <div v-if="message.text" :class="message.type === 'error' ? 'alert alert-error' : 'alert alert-success'">
      {{ message.text }}
    </div>

    <div style="margin-bottom:24px;">
      <button class="btn btn-primary" :disabled="loading" @click="handleBackup">
        {{ loading ? '备份中...' : '立即备份' }}
      </button>
      <span style="color:#888;margin-left:12px;font-size:13px;">
        备份路径: /data/fi_db_backup/
      </span>
    </div>

    <table v-if="backups.length > 0">
      <thead>
        <tr>
          <th>文件名</th>
          <th>大小</th>
          <th>备份时间</th>
          <th style="width:80px;">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="b in backups" :key="b.name">
          <td>{{ b.name }}</td>
          <td>{{ b.sizeStr }}</td>
          <td>{{ b.timeStr }}</td>
          <td>
            <button
              class="btn btn-sm btn-danger"
              :disabled="deleting === b.name"
              @click="handleDelete(b.name)"
            >
              {{ deleting === b.name ? '删除中' : '删除' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state" style="padding:60px 20px;font-size:15px;">
      暂无备份记录，点击上方按钮创建备份
    </div>
  </div>
</template>
