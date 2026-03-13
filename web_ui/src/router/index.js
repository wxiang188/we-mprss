import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/mps'
  },
  {
    path: '/mps',
    name: 'Mps',
    component: () => import('@/views/MpsView.vue')
  },
  {
    path: '/articles',
    name: 'Articles',
    component: () => import('@/views/ArticlesView.vue')
  },
  {
    path: '/tags',
    name: 'Tags',
    component: () => import('@/views/TagsView.vue')
  },
  {
    path: '/export',
    name: 'Export',
    component: () => import('@/views/ExportView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
