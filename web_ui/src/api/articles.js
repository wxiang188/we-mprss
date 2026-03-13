import http from './http'

export const getArticles = (params) => {
  return http.get('/wx/articles', { params })
}

export const getArticle = (articleId) => {
  return http.get(`/wx/articles/${articleId}`)
}

export const updateArticle = (articleId, data) => {
  return http.put(`/wx/articles/${articleId}`, data)
}

export const deleteArticle = (articleId) => {
  return http.delete(`/wx/articles/${articleId}`)
}

export const markRead = (articleId) => {
  return http.post(`/wx/articles/${articleId}/read`)
}

export const getCategories = () => {
  return http.get('/wx/articles/categories/all')
}

export const getAllTags = () => {
  return http.get('/wx/articles/tags/all')
}
