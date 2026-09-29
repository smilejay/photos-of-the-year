<template>
  <div>
    <div class="admin-layout">
      <div class="sidebar card">
        <h3>添加新照片</h3>
        <form @submit.prevent="handleSubmit" enctype="multipart/form-data">
          <div class="form-group">
            <label>年份 * <span class="hint">（根据拍摄日期自动生成）</span></label>
            <input v-model.number="form.year" type="number" readonly disabled>
          </div>
          <div class="form-group">
            <label>拍摄日期 *</label>
            <DatePicker v-model="form.shoot_date" placeholder="点击选择拍摄日期" />
          </div>
          <div class="form-group">
            <label>标题（可选）</label>
            <input v-model="form.title" type="text" placeholder="给这张照片起个标题">
          </div>
          <div class="form-group">
            <label>备注（可选，最多200字）</label>
            <textarea v-model="form.description" maxlength="200" placeholder="一些描述信息"></textarea>
            <small>{{ form.description.length }}/200</small>
          </div>
          <div class="form-group">
            <label>照片文件 *</label>
            <input ref="fileInput" type="file" accept="image/*" required @change="handleFileChange">
          </div>
          <div v-if="error" class="error-message">{{ error }}</div>
          <div v-if="success" class="success-message">{{ success }}</div>
          <button type="submit" class="btn btn-success" :disabled="submitting">
            {{ submitting ? '上传中...' : '上传照片' }}
          </button>
          <button type="button" class="btn btn-secondary ml-1" @click="resetForm">重置</button>
        </form>
      </div>

      <div class="main-content">
        <div class="filter-section card mb-2">
          <label>选择年份：</label>
          <MultiSelectFilter v-model="selectedYears" :options="yearOptions" noun="年份" @change="loadPhotos" />
          <template v-if="isAdmin">
            <label>上传者：</label>
            <MultiSelectFilter v-model="selectedUploaders" :options="uploaderOptions" noun="上传者" @change="loadPhotos" />
          </template>
          <span class="count-info" v-if="selectedYears.length === 1">
            当前已上传 {{ photoCount() }}/10 张
          </span>
        </div>

        <div v-if="loading" class="text-center mt-2">
          <p>加载中...</p>
        </div>

        <div v-else class="photo-list">
          <div v-for="group in groupedPhotos" :key="group.year" class="year-section">
            <h3 class="year-title">{{ group.year }} 年</h3>
            <div v-for="photo in group.photos" :key="photo.id" class="photo-item card">
              <div class="photo-item-image">
                <img :src="photo.thumbnail_url" :alt="photo.title" loading="lazy" @click="openModal(photo)">
                <div class="original-link">
                  <a :href="getOriginalUrl(photo)" target="_blank" rel="noopener noreferrer">查看原图</a>
                </div>
              </div>
              <div class="photo-item-info">
                <p class="uploader-info">上传者：{{ photo.uploader || '未知' }}</p>
                <div class="form-group">
                  <label>标题</label>
                  <input v-model="editForm[photo.id].title" type="text">
                </div>
                <div class="form-group">
                  <label>拍摄日期</label>
                  <DatePicker v-model="editForm[photo.id].shoot_date" placeholder="点击选择拍摄日期" />
                </div>
                <div class="form-group">
                  <label>备注 (最多200字)</label>
                  <textarea v-model="editForm[photo.id].description" maxlength="200"></textarea>
                </div>
                <div class="actions" v-if="canManage(photo)">
                  <button class="btn btn-primary" @click="updatePhoto(photo.id)" :disabled="updating[photo.id]">
                    {{ updating[photo.id] ? '保存中...' : '保存修改' }}
                  </button>
                  <button class="btn btn-danger" @click="deletePhoto(photo.id)" :disabled="updating[photo.id]">
                    删除
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="photos.length === 0" class="empty-state text-center mt-2">
            <p>该年份暂无照片</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal for full-size view -->
    <div v-if="modalPhoto" class="modal" @click.self="closeModal">
      <div class="modal-content">
        <span class="close" @click="closeModal">&times;</span>
        <img :src="modalPhoto.image_url" :alt="modalPhoto.title">
        <div class="modal-info">
          <h3 v-if="modalPhoto.title">{{ modalPhoto.title }}</h3>
          <p class="date">拍摄日期：{{ modalPhoto.shoot_date }} <span class="original-link-inline"><a :href="getOriginalUrl(modalPhoto)" target="_blank" rel="noopener noreferrer">查看原图</a></span></p>
          <p v-if="modalPhoto.description">{{ modalPhoto.description }}</p>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!pendingDeleteId"
      title="删除照片"
      message="确定要删除这张照片吗？删除后无法恢复！"
      confirm-text="删除"
      danger
      @confirm="confirmDelete"
      @cancel="pendingDeleteId = null"
    />
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import axios from 'axios'
import MultiSelectFilter from '../components/MultiSelectFilter.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import DatePicker from '../components/DatePicker.vue'
import { useAuthStore } from '../stores/auth'

export default {
  components: { MultiSelectFilter, ConfirmDialog, DatePicker },
  setup() {
    const authStore = useAuthStore()
    const isAdmin = computed(() => authStore.isAdmin)
    const currentUserId = computed(() => authStore.user?.id)

    const form = reactive({
      year: new Date().getFullYear(),
      title: '',
      description: '',
      shoot_date: '',
      file: null
    })

    const photos = ref([])
    const years = ref([])
    const uploaders = ref([])
    const selectedYears = ref([])
    const selectedUploaders = ref([])
    const loading = ref(true)
    const submitting = ref(false)
    const error = ref('')
    const success = ref('')
    const updating = reactive({})
    const editForm = reactive({})
    const modalPhoto = ref(null)
    const pendingDeleteId = ref(null)

    // 年份/上传者转成通用筛选组件的选项格式
    const yearOptions = computed(() =>
      [...years.value].sort((a, b) => b - a).map(y => ({ value: y, label: `${y} 年` }))
    )
    const uploaderOptions = computed(() =>
      uploaders.value.map(u => ({ value: u.id, label: u.username }))
    )

    // 按年份分组照片（降序），用于管理列表的年份分割
    const groupedPhotos = computed(() => {
      const grouped = {}
      photos.value.forEach(photo => {
        const year = parseInt(photo.shoot_date.substring(0, 4), 10)
        if (!grouped[year]) {
          grouped[year] = []
        }
        grouped[year].push(photo)
      })
      return Object.keys(grouped)
        .map(key => ({ year: Number(key), photos: grouped[key] }))
        .sort((a, b) => b.year - a.year)
    })

    onMounted(async () => {
      await loadYears()
      if (isAdmin.value) {
        await loadUploaders()
      }
      await loadPhotos()
    })

    // 是否可管理某张照片：管理员可管理全部，普通用户仅限自己上传的
    const canManage = (photo) => {
      return isAdmin.value || photo.uploader_id === currentUserId.value
    }

    const photoCount = () => {
      return photos.value.length
    }

    const fileInput = ref(null)

    const handleFileChange = (e) => {
      form.file = e.target.files[0]
    }

    // 监听拍摄日期变化，自动提取年份
    const updateYearFromDate = () => {
      if (form.shoot_date && form.shoot_date.length >= 4) {
        const year = parseInt(form.shoot_date.substring(0, 4), 10)
        if (!isNaN(year)) {
          form.year = year
        }
      }
    }

    // 监听拍摄日期变化自动更新年份
    watch(() => form.shoot_date, updateYearFromDate)

    const loadYears = async () => {
      try {
        const response = await axios.get('/api/years')
        years.value = response.data
        // 默认不选中，不选中时返回全部照片
        selectedYears.value = []
      } catch (err) {
        console.error('Failed to load years', err)
      }
    }

    const loadUploaders = async () => {
      try {
        const response = await axios.get('/api/uploaders')
        uploaders.value = response.data
        selectedUploaders.value = []
      } catch (err) {
        console.error('Failed to load uploaders', err)
      }
    }

    const loadPhotos = async () => {
      loading.value = true
      try {
        const params = []
        selectedYears.value.forEach(year => params.push(`year=${year}`))
        if (isAdmin.value) {
          // 管理员可按上传者筛选
          selectedUploaders.value.forEach(uid => params.push(`uploader=${uid}`))
        } else {
          // 普通用户只看自己上传的照片
          params.push(`uploader=${currentUserId.value}`)
        }
        let url = '/api/photos'
        if (params.length > 0) {
          url += `?${params.join('&')}`
        }
        const response = await axios.get(url)
        photos.value = response.data

        // 初始化编辑表单
        photos.value.forEach(photo => {
          editForm[photo.id] = {
            title: photo.title,
            description: photo.description,
            shoot_date: photo.shoot_date
          }
        })
      } catch (err) {
        console.error('Failed to load photos', err)
      } finally {
        loading.value = false
      }
    }

    const handleSubmit = async () => {
      error.value = ''
      success.value = ''
      submitting.value = true

      if (!form.shoot_date) {
        error.value = '请选择拍摄日期'
        submitting.value = false
        return
      }

      if (!form.file) {
        error.value = '请选择照片文件'
        submitting.value = false
        return
      }

      const formData = new FormData()
      formData.append('year', form.year)
      formData.append('title', form.title)
      formData.append('description', form.description)
      formData.append('shoot_date', form.shoot_date)
      formData.append('file', form.file)

      try {
        const response = await axios.post('/api/photos', formData)
        if (response.data.success) {
          success.value = '上传成功！'
          resetForm()
          loadPhotos()
          loadYears()
          if (isAdmin.value) loadUploaders()
        } else {
          error.value = response.data.message
        }
      } catch (err) {
        error.value = err.response?.data?.message || '上传失败，请重试'
      } finally {
        submitting.value = false
      }
    }

    const updatePhoto = async (photoId) => {
      updating[photoId] = true
      try {
        await axios.put(`/api/photos/${photoId}`, {
          title: editForm[photoId].title,
          description: editForm[photoId].description,
          shoot_date: editForm[photoId].shoot_date
        })
        // 刷新列表
        await loadPhotos()
        success.value = '修改已保存'
        setTimeout(() => success.value = '', 3000)
      } catch (err) {
        error.value = err.response?.data?.message || '保存失败'
      } finally {
        updating[photoId] = false
      }
    }

    const deletePhoto = (photoId) => {
      pendingDeleteId.value = photoId
    }

    const confirmDelete = async () => {
      const photoId = pendingDeleteId.value
      pendingDeleteId.value = null
      if (!photoId) return
      try {
        await axios.delete(`/api/photos/${photoId}`)
        await loadPhotos()
        await loadYears()
        if (isAdmin.value) await loadUploaders()
        success.value = '删除成功'
        setTimeout(() => success.value = '', 3000)
      } catch (err) {
        error.value = err.response?.data?.message || '删除失败'
      }
    }

    const resetForm = () => {
      form.year = new Date().getFullYear()
      form.title = ''
      form.description = ''
      form.shoot_date = ''
      form.file = null
      if (fileInput.value) {
        fileInput.value.value = ''
      }
      error.value = ''
      success.value = ''
    }

    const openModal = (photo) => {
      modalPhoto.value = photo
    }

    const closeModal = () => {
      modalPhoto.value = null
    }

    const getOriginalUrl = (photo) => {
      return `${window.location.origin}${photo.image_url}`
    }

    return {
      form,
      isAdmin,
      canManage,
      photos,
      years,
      uploaders,
      selectedYears,
      selectedUploaders,
      yearOptions,
      uploaderOptions,
      groupedPhotos,
      loading,
      submitting,
      error,
      success,
      updating,
      editForm,
      fileInput,
      modalPhoto,
      pendingDeleteId,
      photoCount,
      handleFileChange,
      handleSubmit,
      loadPhotos,
      updatePhoto,
      deletePhoto,
      confirmDelete,
      resetForm,
      openModal,
      closeModal,
      getOriginalUrl
    }
  }
}
</script>

<style scoped>
.admin-layout {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 2rem;
}

.sidebar {
  position: sticky;
  top: 2rem;
  align-self: start;
}

.sidebar h3 {
  margin-top: 0;
}

.ml-1 {
  margin-left: 0.5rem;
}

small {
  color: #666;
}

.filter-section {
  padding: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.filter-section label {
  font-weight: bold;
}

.count-info {
  color: #666;
  font-size: 0.9rem;
}

.hint {
  color: #999;
  font-weight: normal;
  font-size: 0.9rem;
}

.photo-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.year-section {
  margin-bottom: 2rem;
}

.year-title {
  font-size: 1.5rem;
  color: #333;
  border-bottom: 2px solid #ddd;
  padding-bottom: 0.5rem;
  margin-bottom: 1.5rem;
}

.year-section .photo-item {
  margin-bottom: 1rem;
}

.photo-item {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 1.5rem;
  align-items: start;
}

.photo-item-image {
  width: 300px;
  position: sticky;
  top: 2rem;
}

.photo-item-image img {
  width: 100%;
  height: auto;
  border-radius: 4px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.photo-item-image img:hover {
  opacity: 0.8;
}

.photo-item-info {
  padding-top: 0.5rem;
}

.uploader-info {
  color: #666;
  font-size: 0.9rem;
  margin: 0 0 0.75rem 0;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.25rem;
}

.form-group input[type="text"],
.form-group input[type="number"] {
  font-size: 1.5em;
  padding: 0.375rem;
}

/* 自定义日期选择器触发框尺寸与其它输入一致 */
.form-group :deep(.dp-input) {
  font-size: 1.5em;
  padding: 0.5rem 0.375rem;
}

.form-group textarea {
  font-size: 1rem;
  padding: 0.375rem;
}

.original-link {
  margin: 0.5rem 0 0 0;
  padding: 0;
  text-align: center;
}

.original-link a {
  color: #007bff;
  text-decoration: none;
  font-size: 0.9rem;
}

.original-link a:hover {
  text-decoration: underline;
}

.actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.empty-state {
  padding: 3rem;
  color: #666;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.9);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 2rem;
}

.modal-content {
  max-width: 90%;
  max-height: 90%;
  background-color: white;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

.modal-content img {
  max-width: 100%;
  max-height: 70vh;
  display: block;
  margin: 0 auto;
}

.close {
  position: absolute;
  top: 10px;
  right: 20px;
  color: white;
  font-size: 30px;
  font-weight: bold;
  cursor: pointer;
  text-shadow: 0 0 4px rgba(0,0,0,0.8);
}

.modal-info {
  padding: 1.5rem;
}

.modal-info h3 {
  margin-top: 0;
}

.modal-info .date {
  color: #666;
  font-size: 0.9rem;
  margin: 0.25rem 0;
}

@media (max-width: 900px) {
  .admin-layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: static;
  }

  .photo-item {
    grid-template-columns: 1fr;
  }

  .photo-item-image {
    width: 100%;
    position: static;
  }
}
</style>
