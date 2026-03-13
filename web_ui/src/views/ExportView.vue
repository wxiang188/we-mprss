<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">数据导出</h1>
    </div>

    <a-row :gutter="24">
      <!-- 导出公众号列表 -->
      <a-col :span="12">
        <a-card title="导出公众号列表">
          <p>将所有公众号信息导出为 CSV 格式</p>
          <a-form layout="vertical">
            <a-form-item label="搜索公众号（可选）">
              <a-input v-model:value="mpKw" placeholder="搜索公众号名称" />
            </a-form-item>
            <a-button type="primary" :loading="exportingMp" @click="exportMps">
              <template #icon><ExportOutlined /></template>
              导出 CSV
            </a-button>
          </a-form>
        </a-card>
      </a-col>

      <!-- 导出标签列表 -->
      <a-col :span="12">
        <a-card title="导出标签列表">
          <p>将所有标签信息导出为 CSV 格式</p>
          <a-button type="primary" :loading="exportingTag" @click="exportTags">
            <template #icon><ExportOutlined /></template>
            导出 CSV
          </a-button>
        </a-card>
      </a-col>

      <!-- 导出文章列表 -->
      <a-col :span="24" style="margin-top: 24px">
        <a-card title="导出文章列表">
          <p>将文章列表导出为 CSV 或 JSON 格式</p>
          <a-form layout="vertical">
            <a-row :gutter="16">
              <a-col :span="8">
                <a-form-item label="选择公众号（可选）">
                  <a-select v-model:value="articleMpId" placeholder="全部公众号" allowClear>
                    <a-select-option v-for="mp in mps" :key="mp.id" :value="mp.id">
                      {{ mp.mp_name }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="导出格式">
                  <a-select v-model:value="articleFormat" placeholder="选择格式">
                    <a-select-option value="csv">CSV</a-select-option>
                    <a-select-option value="json">JSON</a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="文章数量">
                  <a-input-number v-model:value="articleLimit" :min="1" :max="5000" style="width: 100%" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-button type="primary" :loading="exportingArticle" @click="exportArticles">
              <template #icon><ExportOutlined /></template>
              导出文章列表
            </a-button>
          </a-form>
        </a-card>
      </a-col>

      <!-- 导出文章详细内容 -->
      <a-col :span="24" style="margin-top: 24px">
        <a-card title="导出文章详细内容">
          <p>将文章详细内容打包为 ZIP（包含 CSV、JSON、Markdown）</p>
          <a-form layout="vertical">
            <a-row :gutter="16">
              <a-col :span="8">
                <a-form-item label="选择公众号">
                  <a-select v-model:value="detailMpId" placeholder="全部公众号" allowClear>
                    <a-select-option v-for="mp in mps" :key="mp.id" :value="mp.id">
                      {{ mp.mp_name }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="文章数量">
                  <a-input-number v-model:value="detailLimit" :min="1" :max="100" style="width: 100%" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="16">
              <a-col>
                <a-checkbox v-model:checked="includeCsv">包含 CSV</a-checkbox>
                <a-checkbox v-model:checked="includeJson">包含 JSON</a-checkbox>
                <a-checkbox v-model:checked="includeMd">包含 Markdown</a-checkbox>
              </a-col>
            </a-row>
            <a-button type="primary" :loading="exportingDetail" @click="exportArticleDetails" style="margin-top: 16px">
              <template #icon><ExportOutlined /></template>
              导出详细内容
            </a-button>
          </a-form>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { ExportOutlined } from '@ant-design/icons-vue'
import { getMps } from '@/api/mps'
import { exportMps, exportTags, exportArticles, exportArticlesZip } from '@/api/export'

const mps = ref([])

// 公众号导出
const mpKw = ref('')
const exportingMp = ref(false)

// 标签导出
const exportingTag = ref(false)

// 文章列表导出
const articleMpId = ref(null)
const articleFormat = ref('csv')
const articleLimit = ref(100)
const exportingArticle = ref(false)

// 文章详细内容导出
const detailMpId = ref(null)
const detailLimit = ref(10)
const includeCsv = ref(true)
const includeJson = ref(true)
const includeMd = ref(false)
const exportingDetail = ref(false)

const loadMps = async () => {
  try {
    const res = await getMps({ limit: 100 })
    mps.value = res.data?.list || []
  } catch (e) {
    console.error(e)
  }
}

const downloadFile = (response, filename) => {
  const blob = new Blob([response.data], { type: response.headers['content-type'] })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

const exportMpsHandler = async () => {
  exportingMp.value = true
  try {
    const res = await exportMps()
    downloadFile(res, '公众号列表.csv')
    message.success('导出成功')
  } catch (e) {
    console.error(e)
  } finally {
    exportingMp.value = false
  }
}

const exportTagsHandler = async () => {
  exportingTag.value = true
  try {
    const res = await exportTags()
    downloadFile(res, '标签列表.csv')
    message.success('导出成功')
  } catch (e) {
    console.error(e)
  } finally {
    exportingTag.value = false
  }
}

const exportArticlesHandler = async () => {
  exportingArticle.value = true
  try {
    const res = await exportArticles({
      mp_id: articleMpId.value,
      format: articleFormat.value,
      limit: articleLimit.value
    })
    const ext = articleFormat.value === 'csv' ? 'csv' : 'json'
    downloadFile(res, `文章列表.${ext}`)
    message.success('导出成功')
  } catch (e) {
    console.error(e)
  } finally {
    exportingArticle.value = false
  }
}

const exportArticleDetailsHandler = async () => {
  exportingDetail.value = true
  try {
    const res = await exportArticlesZip({
      mp_id: detailMpId.value,
      limit: detailLimit.value,
      export_csv: includeCsv.value,
      export_json: includeJson.value,
      export_md: includeMd.value
    })
    downloadFile(res, `文章导出_${Date.now()}.zip`)
    message.success('导出成功')
  } catch (e) {
    console.error(e)
  } finally {
    exportingDetail.value = false
  }
}

onMounted(() => {
  loadMps()
})
</script>
