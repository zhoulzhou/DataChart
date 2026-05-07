import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/public/Dashboard.vue'
import Login from '../views/admin/Login.vue'
import CompanyManage from '../views/admin/CompanyManage.vue'
import DataEntry from '../views/admin/DataEntry.vue'
import DataList from '../views/admin/DataList.vue'
import Backup from '../views/admin/Backup.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/login', name: 'Login', component: Login },
  { path: '/admin/companies', name: 'CompanyManage', component: CompanyManage, meta: { requiresAuth: true } },
  { path: '/admin/data-entry', name: 'DataEntry', component: DataEntry, meta: { requiresAuth: true } },
  { path: '/admin/data-list', name: 'DataList', component: DataList, meta: { requiresAuth: true } },
  { path: '/admin/backup', name: 'Backup', component: Backup, meta: { requiresAuth: true } }
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
