import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/public/Dashboard.vue') },
  { path: '/login', name: 'Login', component: () => import('../views/admin/Login.vue') },
  { path: '/admin/companies', name: 'CompanyManage', component: () => import('../views/admin/CompanyManage.vue'), meta: { requiresAuth: true } },
  { path: '/admin/data-entry', name: 'DataEntry', component: () => import('../views/admin/DataEntry.vue'), meta: { requiresAuth: true } },
  { path: '/admin/data-list', name: 'DataList', component: () => import('../views/admin/DataList.vue'), meta: { requiresAuth: true } },
  { path: '/admin/backup', name: 'Backup', component: () => import('../views/admin/Backup.vue'), meta: { requiresAuth: true } },
  { path: '/admin/stock-fetch', name: 'StockFetch', component: () => import('../views/admin/StockFetch.vue'), meta: { requiresAuth: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('token')
    if (!token) {
      return next('/login')
    }
  }
  if (to.path === '/login') {
    const token = localStorage.getItem('token')
    if (token) {
      return next('/admin/companies')
    }
  }
  next()
})

export default router
