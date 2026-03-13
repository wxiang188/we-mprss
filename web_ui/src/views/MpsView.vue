<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">公众号管理</h1>
      <a-space>
        <a-button type="primary" @click="showAddModal">
          <template #icon><PlusOutlined /></template>
          添加公众号
        </a-button>
        <a-button @click="loadMps">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </a-space>
    </div>

    <!-- 搜索栏 -->
    <div class="table-operations">
      <a-input-search
        v-model:value="searchKw"
        placeholder="搜索公众号名称"
        style="width: 300px"
        @search="loadMps"
      />
    </div>

    <!-- 公众号列表 -->
    <a-row :gutter="16">
      <a-col :span="8" v-for="mp in mps" :key="mp.id">
        <a-card class="mp-card" :bordered="false" hoverable>
          <template #cover>
            <img :src="mp.mp_cover || defaultCover" style="height: 120px; object-fit: cover" />
          </template>
          <a-card-meta :title="mp.mp_name">
            <template #description>
              <p>{{ mp.mp_intro || '暂无简介' }}</p>
              <p style="color: #999; font-size: 12px">
                创建时间: {{ formatDate(mp.created_at) }}
              </p>
            </template>
          </a-card-meta>
          <template #actions>
            <a-tooltip title="同步文章">
              <SyncOutlined @click.stop="syncMp(mp.id)" />
            </a-tooltip>
            <a-tooltip title="查看文章">
              <EyeOutlined @click.stop="viewArticles(mp.id)" />
            </a-tooltip>
            <a-tooltip title="删除">
              <DeleteOutlined @click.stop="deleteMp(mp.id)" />
            </a-tooltip>
          </template>
        </a-card>
      </a-col>
    </a-row>

    <!-- 空状态 -->
    <a-empty v-if="mps.length === 0" description="暂无公众号，请添加" />

    <!-- 添加公众号弹窗 -->
    <a-modal
      v-model:open="addModalVisible"
      title="添加公众号"
      width="700px"
      :footer="null"
    >
      <a-tabs v-model:activeKey="addTab">
        <a-tab-pane key="byQrcode" tab="扫码授权">
          <div class="qrcode-login">
            <div v-if="!isLoggedIn" class="qrcode-section">
              <p>点击下方按钮获取二维码，使用微信扫描登录</p>
              <a-button type="primary" size="large" @click="getQrcode" :loading="qrcodeLoading">
                <template #icon><QrcodeOutlined /></template>
                获取二维码
              </a-button>

              <div v-if="qrcode" class="qrcode-display">
                <img :src="qrcode" alt="登录二维码" />
                <p class="qrcode-tip">请使用微信扫描二维码登录</p>
              </div>
            </div>

            <div v-else class="account-list-section">
              <a-alert type="success" message="登录成功！请选择要添加的公众号" show-icon />

              <a-list :data-source="wxAccounts" :loading="accountsLoading" style="margin-top: 16px">
                <template #renderItem="{ item }">
                  <a-list-item>
                    <a-list-item-meta>
                      <template #avatar>
                        <img :src="item.headimgurl || defaultCover" style="width: 48px; height: 48px; border-radius: 50%" />
                      </template>
                      <template #title>{{ item.nickname }}</template>
                      <template #description>{{ item.user_name }}</template>
                    </a-list-item-meta>
                    <template #actions>
                      <a-button type="primary" size="small" @click="addMpFromAccount(item)">添加</a-button>
                    </template>
                  </a-list-item>
                </template>
              </a-list>

              <a-button style="margin-top: 16px" @click="isLoggedIn = false">重新扫码</a-button>
            </div>
          </div>
        </a-tab-pane>

        <a-tab-pane key="byId" tab="手动输入">
          <a-form :model="addForm" layout="vertical">
            <a-form-item label="公众号ID (Faker ID)" required>
              <a-input v-model:value="addForm.faker_id" placeholder="请输入公众号的 Faker ID" />
            </a-form-item>
            <a-form-item label="公众号名称">
              <a-input v-model:value="addForm.mp_name" placeholder="留空则自动获取" />
            </a-form-item>
            <a-form-item label="简介">
              <a-textarea v-model:value="addForm.mp_intro" placeholder="公众号简介" :rows="2" />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="handleAddMp" :loading="addLoading">添加</a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="byArticle" tab="通过文章链接获取">
          <a-form layout="vertical">
            <a-form-item label="微信公众号文章链接">
              <a-input
                v-model:value="articleUrl"
                placeholder="请输入微信公众号文章链接，如：https://mp.weixin.qq.com/s/xxx"
              >
                <template #append>
                  <a-button @click="fetchMpByArticle" :loading="fetching">
                    获取
                  </a-button>
                </template>
              </a-input>
            </a-form-item>

            <a-divider v-if="mpInfo.mp_name">获取到的公众号信息</a-divider>

            <div v-if="mpInfo.mp_name" class="mp-preview">
              <a-row :gutter="16" align="middle">
                <a-col :span="4">
                  <img
                    :src="mpInfo.mp_cover || defaultCover"
                    style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover"
                  />
                </a-col>
                <a-col :span="20">
                  <div style="font-size: 16px; font-weight: bold">{{ mpInfo.mp_name }}</div>
                  <div style="color: #999; font-size: 12px; margin-top: 4px">
                    {{ mpInfo.mp_intro || '暂无简介' }}
                  </div>
                </a-col>
              </a-row>
              <div style="margin-top: 16px">
                <a-button type="primary" @click="addMpFromArticle">添加此公众号</a-button>
              </div>
            </div>
          </a-form>
        </a-tab-pane>
      </a-tabs>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { PlusOutlined, ReloadOutlined, SyncOutlined, EyeOutlined, DeleteOutlined, QrcodeOutlined } from '@ant-design/icons-vue'
import { getMps, addMp, deleteMp, syncMp, getMpByArticle } from '@/api/mps'

const router = useRouter()

const mps = ref([])
const searchKw = ref('')
const addModalVisible = ref(false)
const addLoading = ref(false)
const addTab = ref('byQrcode')
const addForm = ref({
  faker_id: '',
  mp_name: '',
  mp_intro: ''
})

// 扫码登录相关
const qrcodeLoading = ref(false)
const qrcode = ref('')
const isLoggedIn = ref(false)
const wxAccounts = ref([])
const accountsLoading = ref(false)
let scanTimer = null

// 通过文章链接获取
const articleUrl = ref('')
const fetching = ref(false)
const mpInfo = ref({
  mp_name: '',
  mp_cover: '',
  mp_intro: '',
  mp_id: ''
})

const defaultCover = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMjAiIGhlaWdodD0iMTIwIj48cmVjdCB3aWR0aD0iMTIwIiBoZWlnaHQ9IjEyMCIgZmlsbD0iI2YzZjRmNiIvPjx0ZXh0IHg9IjUwIiB5PSI1MCIgZm9udC1zaXplPSIyNCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iI2MzYzJhZiI+5raI5oGvPC90ZXh0Pjwvc3ZnPg=='

const loadMps = async () => {
  try {
    const res = await getMps({ limit: 100, kw: searchKw.value })
    mps.value = res.data?.list || []
  } catch (e) {
    console.error(e)
  }
}

const showAddModal = () => {
  addForm.value = { faker_id: '', mp_name: '', mp_intro: '' }
  articleUrl.value = ''
  mpInfo.value = { mp_name: '', mp_cover: '', mp_intro: '', mp_id: '' }
  addTab.value = 'byQrcode'
  addModalVisible.value = true
  checkLoginStatus()
}

// 扫码登录相关函数
const getQrcode = async () => {
  qrcodeLoading.value = true
  try {
    const res = await fetch('/api/wx/mps/scan-qrcode', { method: 'POST' })
    const data = await res.json()
    if (data.code === 0 && data.data.qrcode) {
      qrcode.value = data.data.qrcode
      // 启动轮询检查登录状态
      startScanCheck()
    } else {
      message.error(data.message || '获取二维码失败')
    }
  } catch (e) {
    console.error(e)
    message.error('获取二维码失败')
  } finally {
    qrcodeLoading.value = false
  }
}

const startScanCheck = () => {
  if (scanTimer) clearInterval(scanTimer)
  scanTimer = setInterval(checkLoginStatus, 2000)
}

const checkLoginStatus = async () => {
  try {
    const res = await fetch('/api/wx/mps/scan-status')
    const data = await res.json()
    if (data.data && data.data.is_logged_in) {
      isLoggedIn.value = true
      if (scanTimer) {
        clearInterval(scanTimer)
        scanTimer = null
      }
      // 获取公众号列表
      loadWxAccounts()
    }
  } catch (e) {
    console.error(e)
  }
}

const loadWxAccounts = async () => {
  accountsLoading.value = true
  try {
    const res = await fetch('/api/wx/mps/account-list')
    const data = await res.json()
    if (data.code === 0 && data.data && data.data.list) {
      wxAccounts.value = data.data.list
    }
  } catch (e) {
    console.error(e)
  } finally {
    accountsLoading.value = false
  }
}

const addMpFromAccount = async (account) => {
  try {
    await addMp({
      faker_id: account.user_name,
      mp_name: account.nickname,
      mp_cover: account.headimgurl,
      mp_intro: ''
    })
    message.success('添加成功')
    loadMps()
  } catch (e) {
    console.error(e)
  }
}

const handleAddMp = async () => {
  if (!addForm.value.faker_id) {
    message.error('请输入公众号ID')
    return
  }
  addLoading.value = true
  try {
    await addMp(addForm.value)
    message.success('添加成功')
    addModalVisible.value = false
    loadMps()
  } catch (e) {
    console.error(e)
  } finally {
    addLoading.value = false
  }
}

const fetchMpByArticle = async () => {
  if (!articleUrl.value) {
    message.error('请输入微信公众号文章链接')
    return
  }

  if (!articleUrl.value.includes('mp.weixin.qq.com')) {
    message.error('请输入正确的微信公众号文章链接')
    return
  }

  fetching.value = true
  try {
    const res = await getMpByArticle(articleUrl.value)
    if (res.data && res.data.mp_name) {
      mpInfo.value = res.data
      message.success('获取成功')
    } else {
      message.warning('未能获取到公众号信息，请检查链接是否正确')
    }
  } catch (e) {
    console.error(e)
    message.error('获取失败，请确保文章链接正确')
  } finally {
    fetching.value = false
  }
}

const addMpFromArticle = async () => {
  try {
    await addMp({
      faker_id: mpInfo.value.mp_id || mpInfo.value.mp_name,
      mp_name: mpInfo.value.mp_name,
      mp_cover: mpInfo.value.mp_cover,
      mp_intro: mpInfo.value.mp_intro
    })
    message.success('添加成功')
    addModalVisible.value = false
    loadMps()
  } catch (e) {
    console.error(e)
  }
}

const deleteMpHandler = (id) => {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这个公众号吗？',
    onOk: async () => {
      try {
        await deleteMp(id)
        message.success('删除成功')
        loadMps()
      } catch (e) {
        console.error(e)
      }
    }
  })
}

const syncMpHandler = async (id) => {
  try {
    await syncMp(id)
    message.success('同步成功')
  } catch (e) {
    console.error(e)
  }
}

const viewArticles = (mpId) => {
  router.push({ path: '/articles', query: { mp_id: mpId } })
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadMps()
})

onUnmounted(() => {
  if (scanTimer) {
    clearInterval(scanTimer)
  }
})
</script>

<style scoped>
.mp-card {
  margin-bottom: 16px;
}

.mp-preview {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 8px;
}

.qrcode-login {
  text-align: center;
  padding: 20px;
}

.qrcode-section {
  padding: 20px;
}

.qrcode-display {
  margin-top: 24px;
}

.qrcode-display img {
  width: 200px;
  height: 200px;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.qrcode-tip {
  margin-top: 12px;
  color: #1890ff;
  font-size: 14px;
}

.account-list-section {
  text-align: left;
}
</style>
