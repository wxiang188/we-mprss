<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">标签管理</h1>
      <a-space>
        <a-button type="primary" @click="showAddModal">
          <template #icon><PlusOutlined /></template>
          添加标签
        </a-button>
        <a-button @click="loadTags">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </a-space>
    </div>

    <!-- 标签列表 -->
    <a-row :gutter="16">
      <a-col :span="6" v-for="tag in tags" :key="tag.id">
        <a-card :bordered="false" hoverable>
          <a-card-meta :title="tag.name">
            <template #description>
              <p>{{ tag.intro || '暂无描述' }}</p>
              <p style="color: #999; font-size: 12px">
                创建时间: {{ formatDate(tag.created_at) }}
              </p>
            </template>
          </a-card-meta>
          <template #actions>
            <a-tooltip title="编辑">
              <EditOutlined @click="editTag(tag)" />
            </a-tooltip>
            <a-tooltip title="删除">
              <DeleteOutlined @click="deleteTag(tag.id)" />
            </a-tooltip>
          </template>
        </a-card>
      </a-col>
    </a-row>

    <!-- 空状态 -->
    <a-empty v-if="tags.length === 0" description="暂无标签" />

    <!-- 添加/编辑标签弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑标签' : '添加标签'"
      @ok="handleSave"
      :confirm-loading="saveLoading"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="标签名称" required>
          <a-input v-model:value="form.name" placeholder="请输入标签名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.intro" placeholder="标签描述" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue'

const tags = ref([])
const modalVisible = ref(false)
const saveLoading = ref(false)
const isEdit = ref(false)
const form = ref({
  id: '',
  name: '',
  intro: ''
})

const loadTags = async () => {
  // TODO: 实现标签列表加载
}

const showAddModal = () => {
  form.value = { id: '', name: '', intro: '' }
  isEdit.value = false
  modalVisible.value = true
}

const editTag = (tag) => {
  form.value = { ...tag }
  isEdit.value = true
  modalVisible.value = true
}

const handleSave = async () => {
  if (!form.value.name) {
    message.error('请输入标签名称')
    return
  }
  saveLoading.value = true
  try {
    // TODO: 实现保存
    message.success('保存成功')
    modalVisible.value = false
    loadTags()
  } catch (e) {
    console.error(e)
  } finally {
    saveLoading.value = false
  }
}

const deleteTagHandler = (id) => {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这个标签吗？',
    onOk: async () => {
      // TODO: 实现删除
      message.success('删除成功')
      loadTags()
    }
  })
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadTags()
})
</script>

<style scoped>
.ant-col {
  margin-bottom: 16px;
}
</style>
