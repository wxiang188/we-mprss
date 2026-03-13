import http from './http'

export const exportMps = () => {
  return http.get('/wx/export/mps', {
    responseType: 'blob'
  })
}

export const exportTags = () => {
  return http.get('/wx/export/tags', {
    responseType: 'blob'
  })
}

export const exportArticles = (params) => {
  return http.get('/wx/export/articles', {
    params,
    responseType: 'blob'
  })
}

export const exportArticlesZip = (data) => {
  return http.post('/wx/export/articles/zip', data, {
    responseType: 'blob'
  })
}
