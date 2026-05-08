<script setup>
import { ref } from 'vue'
import request from '../../api/request'

const code = ref('')
const loading = ref(false)
const result = ref(null)
const message = ref({ type: '', text: '' })

async function handleFetch() {
  if (!code.value.trim()) {
    message.value = { type: 'error', text: '请输入股票代码' }
    return
  }
  loading.value = true
  message.value = { type: '', text: '' }
  result.value = null

  try {
    const res = await request.post('/fetch-financials', { code: code.value.trim() })
    if (res.code === 0) {
      message.value = { type: 'success', text: res.message }
      result.value = res.data
    } else {
      message.value = { type: 'error', text: res.message }
    }
  } catch {
    message.value = { type: 'error', text: '请求失败，请检查网络连接' }
  }
  loading.value = false
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">获取财务数据</h1>
    </div>

    <div v-if="message.text" :class="message.type === 'error' ? 'alert alert-error' : 'alert alert-success'">
      {{ message.text }}
    </div>

    <div class="card" style="max-width:600px;">
      <div class="form-group">
        <label class="form-label">股票代码</label>
        <div style="display:flex;gap:12px;align-items:flex-end;">
          <input
            class="form-input no-spin"
            style="flex:1;"
            type="text"
            v-model="code"
            placeholder="如：300308、300502"
            @keyup.enter="handleFetch"
          />
          <button class="btn btn-primary" :disabled="loading" @click="handleFetch">
            {{ loading ? '获取中...' : '获取数据' }}
          </button>
        </div>
      </div>

      <div v-if="result" class="card" style="background:#f0f9ff;margin-top:16px;padding:16px 20px;">
        <div style="display:flex;gap:32px;font-size:14px;">
          <div><span style="color:#888;">获取</span> <strong>{{ result.total }}</strong> 条</div>
          <div><span style="color:#888;">新增</span> <strong style="color:#2ecc71;">{{ result.inserted }}</strong> 条</div>
          <div><span style="color:#888;">跳过</span> <strong style="color:#f39c12;">{{ result.skipped }}</strong> 条</div>
        </div>
      </div>

      <p style="color:#999;font-size:13px;margin-top:16px;">
        数据来源：东方财富，自动获取近三年季度财报。<br/>
        获取后请前往 <router-link to="/admin/data-list">数据列表</router-link> 查看。
      </p>
    </div>
  </div>
</template>
