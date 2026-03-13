<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">文章列表</h1>
      <a-space>
        <a-button type="primary" @click="showAiModal">
          <template #icon><RobotOutlined /></template>
          AI 批量处理
        </a-button>
        <a-button @click="loadArticles">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </a-space>
    </div>

    <!-- 搜索栏 -->
    <div class="table-operations">
      <a-select
        v-model:value="filterMpId"
        placeholder="选择公众号"
        style="width: 200px"
        allowClear
        @change="loadArticles"
      >
        <a-select-option v-for="mp in mps" :key="mp.id" :value="mp.id">
          {{ mp.mp_name }}
        </a-select-option>
      </a-select>
      <a-input-search
        v-model:value="searchKw"
        placeholder="搜索文章标题"
        style="width: 300px"
        @search="loadArticles"
      />
    </div>

    <!-- 文章列表 -->
    <a-list :data-source="articles" :loading="loading" :pagination="pagination">
      <template #renderItem="{ item }">
        <a-list-item>
          <a-list-item-meta>
            <template #title>
              <a @click="viewArticle(item)">{{ item.title }}</a>
            </template>
            <template #description>
              <div class="article-meta">
                <span><WechatOutlined /> {{ item.mp_name }}</span>
                <span>{{ formatDate(item.publish_time) }}</span>
              </div>
              <div class="tag-list" v-if="item.ai_category || item.ai_tags">
                <a-tag v-if="item.ai_category" color="blue">{{ item.ai_category }}</a-tag>
                <a-tag v-for="tag in parseTags(item.ai_tags)" :key="tag" color="green">
                  {{ tag }}
                </a-tag>
              </div>
              <div v-if="item.ai_summary" class="summary-box">
                <strong>AI 总结：</strong>{{ item.ai_summary }}
              </div>
            </template>
          </a-list-item-meta>
          <template #actions>
            <a-button type="link" size="small" @click="viewArticle(item)">查看</a-button>
            <a-button type="link" size="small" @click="aiProcessArticle(item)">AI处理</a-button>
          </template>
        </a-list-item>
      </template>
    </a-list>

    <!-- AI 处理弹窗 -->
    <a-modal
      v-model:open="aiModalVisible"
      title="AI 批量处理"
      @ok="handleAiProcess"
      :confirm-loading="aiLoading"
    >
      <a-checkbox-group v-model:value="aiOptions">
        <a-checkbox value="summary">AI 总结</a-checkbox>
        <a-checkbox value="category">AI 分类</a-checkbox>
        <a-checkbox value="tags">提取标签</a-checkbox>
      </a-checkbox-group>
      <a-divider />
      <p>已选择 {{ selectedArticles.length }} 篇文章</p>
    </a-modal>

    <!-- 文章详情弹窗 -->
    <a-modal
      v-model:open="detailVisible"
      :title="currentArticle?.title"
      width="800px"
      :footer="null"
    >
      <div v-if="currentArticle">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="公众号">{{ currentArticle.mp_name }}</a-descriptions-item>
          <a-descriptions-item label="发布时间">{{ formatDate(currentArticle.publish_time) }}</a-descriptions-item>
          <a-descriptions-item label="AI 分类">{{ currentArticle.ai_category || '-' }}</a-descriptions-item>
          <a-descriptions-item label="AI 标签">{{ currentArticle.ai_tags || '-' }}</a-descriptions-item>
        </a-descriptions>
        <a-divider>AI 总结</a-divider>
        <div>{{ currentArticle.ai_summary || '暂无' }}</div>
        <a-divider>文章内容</a-divider>
        <div v-html="currentArticle.content"></div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { ReloadOutlined, RobotOutlined, WechatOutlined } from '@ant-design/icons-vue'
import { getArticles, getArticle } from '@/api/articles'
import { aiProcess } from '@/api/ai'
import { getMps } from '@/api/mps'

const route = useRoute()

const articles = ref([])
const mps = ref([])
const loading = ref(false)
const searchKw = ref('')
const filterMpId = ref(route.query.mp_id || null)

// AI 处理
const aiModalVisible = ref(false)
const aiLoading = ref(false)
const aiOptions = ref(['summary', 'category', 'tags'])
const selectedArticles = ref([])

// 文章详情
const detailVisible = ref(false)
const currentArticle = ref(null)

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 条`
})

const loadMps = async () => {
  try {
    const res = await getMps({ limit: 100 })
    mps.value = res.data?.list || []
  } catch (e) {
    console.error(e)
  }
}

const loadArticles = async () => {
  loading.value = true
  try {
    const params = {
      limit: pagination.value.pageSize,
      offset: (pagination.value.current - 1) * pagination.value.pageSize,
      kw: searchKw.value
    }
    if (filterMpId.value) {
      params.mp_id = filterMpId.value
    }
    const res = await getArticles(params)
    articles.value = res.data?.list || []
    pagination.value.total = res.data?.total || 0
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const viewArticle = async (item) => {
  try {
    const res = await getArticle(item.id)
    currentArticle.value = res.data
    detailVisible.value = true
  } catch (e) {
    console.error(e)
  }
}

const showAiModal = () => {
  selectedArticles.value = articles.value.map(a => a.id)
  aiModalVisible.value = true
}

const handleAiProcess = async () => {
  if (selectedArticles.value.length === 0) {
    message.error('请选择文章')
    return
  }
  aiLoading.value = true
  try {
    await aiProcess(selectedArticles.value)
    message.success('AI 处理完成')
    aiModalVisible.value = false
    loadArticles()
  } catch (e) {
    console.error(e)
  } finally {
    aiLoading.value = false
  }
}

const aiProcessArticle = async (item) => {
  try {
    await aiProcess([item.id])
    message.success('AI 处理完成')
    loadArticles()
  } catch (e) {
    console.error(e)
  }
}

const parseTags = (tags) => {
  if (!tags) return []
  try {
    return JSON.parse(tags)
  } catch {
    return []
  }
}

const formatDate = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

onMounted(() => {
  loadMps()
  loadArticles()
})
</script>
