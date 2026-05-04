import request from './request'

export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

export function checkAuth() {
  return request.get('/auth/check')
}
