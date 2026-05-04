import request from './request'

export function getCompanies(params) {
  return request.get('/companies', { params })
}

export function createCompany(data) {
  return request.post('/companies', data)
}

export function updateCompany(id, data) {
  return request.put(`/companies/${id}`, data)
}

export function updateCompanyStatus(id, status) {
  return request.put(`/companies/${id}/status`, { status })
}

export function getPublicCompanies() {
  return request.get('/public/companies')
}

export function deleteCompany(id) {
  return request.delete(`/companies/${id}`)
}
