<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../../api/auth'

const router = useRouter()
const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  if (!form.value.username || !form.value.password) {
    error.value = '请输入账号和密码'
    return
  }
  loading.value = true
  try {
    const res = await login(form.value.username, form.value.password)
    if (res.code === 0) {
      localStorage.setItem('token', res.data.token)
      router.push('/admin/companies')
    } else {
      error.value = res.message
    }
  } catch {
    error.value = '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page" style="display:flex;align-items:center;justify-content:center;min-height:100vh;background:linear-gradient(135deg,#4361ee,#2ec4b6);">
    <div class="card" style="width:380px;padding:40px;">
      <h2 style="text-align:center;margin-bottom:32px;font-size:22px;">财务管理系统</h2>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div class="form-group">
        <label class="form-label">账号</label>
        <input class="form-input" v-model="form.username" placeholder="请输入账号" @keyup.enter="handleLogin" />
      </div>
      <div class="form-group">
        <label class="form-label">密码</label>
        <input class="form-input" type="password" v-model="form.password" placeholder="请输入密码" @keyup.enter="handleLogin" />
      </div>
      <button class="btn btn-primary" style="width:100%;padding:10px;" :disabled="loading" @click="handleLogin">
        {{ loading ? '登录中...' : '登 录' }}
      </button>
    </div>
  </div>
</template>
