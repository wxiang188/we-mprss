<template>
  <a-config-provider :locale="zhCN">
    <a-layout class="layout">
      <a-layout-header class="header">
        <div class="logo">
          <WechatOutlined />
          <span>WeChat MP RSS</span>
        </div>
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="horizontal"
          theme="dark"
          :items="menuItems"
          @click="handleMenuClick"
        />
      </a-layout-header>
      <a-layout-content class="content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { ref, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { WechatOutlined, BookOutlined, FileTextOutlined, ExportOutlined, TagsOutlined } from '@ant-design/icons-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'

const router = useRouter()
const route = useRoute()

const selectedKeys = ref([route.path])

const menuItems = [
  { key: '/mps', icon: () => h(WechatOutlined), label: '公众号管理' },
  { key: '/articles', icon: () => h(FileTextOutlined), label: '文章列表' },
  { key: '/tags', icon: () => h(TagsOutlined), label: '标签管理' },
  { key: '/export', icon: () => h(ExportOutlined), label: '数据导出' }
]

const handleMenuClick = ({ key }) => {
  router.push(key)
  selectedKeys.value = [key]
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.logo {
  color: white;
  font-size: 18px;
  font-weight: bold;
  margin-right: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.content {
  padding: 24px;
  background: #f0f2f5;
  min-height: calc(100vh - 64px);
}
</style>
