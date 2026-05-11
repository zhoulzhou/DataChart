import axios from 'axios'
import { useRouter } from 'vue-router'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      window.$toast?.error('登录已过期，请重新登录')
      const currentPath = window.location.pathname
      window.location.href = '/login?redirect=' + encodeURIComponent(currentPath)
    } else {
      const msg = error.response?.data?.message || error.message || '网络请求失败'
      window.$toast?.error(msg)
    }
    return Promise.reject(error)
  }
)

export default request
