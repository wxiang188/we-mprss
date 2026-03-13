import http from './http'

export const aiSummary = (articleIds) => {
  return http.post('/wx/ai/summary', { article_ids: articleIds })
}

export const aiCategory = (articleIds) => {
  return http.post('/wx/ai/category', { article_ids: articleIds })
}

export const aiTags = (articleIds) => {
  return http.post('/wx/ai/tags', { article_ids: articleIds })
}

export const aiProcess = (articleIds) => {
  return http.post('/wx/ai/process', { article_ids: articleIds })
}

export const aiProcessAll = (params) => {
  return http.post('/wx/ai/process-all', null, { params })
}
