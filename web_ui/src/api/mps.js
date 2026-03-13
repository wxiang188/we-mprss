import http from './http'

export const getMps = (params) => {
  return http.get('/wx/mps', { params })
}

export const getMp = (mpId) => {
  return http.get(`/wx/mps/${mpId}`)
}

export const addMp = (data) => {
  return http.post('/wx/mps', data)
}

export const deleteMp = (mpId) => {
  return http.delete(`/wx/mps/${mpId}`)
}

export const syncMp = (mpId) => {
  return http.post(`/wx/mps/${mpId}/sync`)
}

export const scanQrcode = () => {
  return http.post('/wx/mps/scan-qrcode')
}

export const checkScanStatus = (ticket) => {
  return http.get(`/wx/mps/scan-status/${ticket}`)
}

export const getMpByArticle = (url) => {
  return http.get('/wx/mps/by-article', { params: { url } })
}
