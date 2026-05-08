<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const isAdmin = computed(() => localStorage.getItem('token'))

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<template>
  <div class="nav-bar" v-if="route.path !== '/login'">
    <span class="nav-brand">财务指标可视化</span>
    <router-link to="/">前台展示</router-link>
    <template v-if="isAdmin">
      <router-link to="/admin/companies">公司管理</router-link>
      <router-link to="/admin/data-entry">数据录入</router-link>
      <router-link to="/admin/data-list">数据列表</router-link>
      <router-link to="/admin/backup">数据库备份</router-link>
      <router-link to="/admin/stock-fetch">获取数据</router-link>
    </template>
    <div class="nav-right">
      <template v-if="isAdmin">
        <button class="btn btn-sm btn-outline" @click="logout">退出登录</button>
      </template>
      <template v-else>
        <router-link to="/login">后台登录</router-link>
      </template>
    </div>
  </div>
  <router-view />
</template>
