import request from './request'

export function getFinancials(params) {
  return request.get('/financials', { params })
}

export function createFinancial(data) {
  return request.post('/financials', data)
}

export function updateFinancial(id, data) {
  return request.put(`/financials/${id}`, data)
}

export function deleteFinancial(id) {
  return request.delete(`/financials/${id}`)
}

export function getPublicFinancials(params) {
  return request.get('/public/financials', { params })
}
