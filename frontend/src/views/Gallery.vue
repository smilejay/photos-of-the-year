<template>
  <div>
    <div v-if="loading" class="text-center mt-2">
      <p>加载中...</p>
    </div>

    <div v-else>
      <div class="year-filter">
        <label>选择年份：</label>
        <MultiSelectFilter v-model="selectedYears" :options="yearOptions" noun="年份" @change="loadPhotos" />
        <label>上传者：</label>
        <MultiSelectFilter v-model="selectedUploaders" :options="uploaderOptions" noun="上传者" @change="loadPhotos" />
      </div>

      <div v-if="photos.length === 0" class="empty-state text-center mt-2">
        <p>暂无照片</p>
      </div>

      <div v-for="group in groupedPhotos" :key="group.year" class="year-section">
        <h3 class="year-title">{{ group.year }} 年</h3>
        <div class="photo-grid">
          <div v-for="photo in group.photos" :key="photo.id" class="photo-card card">
            <div class="photo-container">
              <img :src="photo.thumbnail_url" :alt="photo.title || '照片'" loading="lazy" @click="openModal(photo)">
            </div>
            <div class="photo-info">
              <h4 v-if="photo.title">{{ photo.title }}</h4>
              <p class="date">拍摄日期：{{ photo.shoot_date }} <span class="original-link-inline"><a :href="getOriginalUrl(photo)" target="_blank" rel="noopener noreferrer">查看原图</a></span></p>
              <p class="uploader">上传者：{{ photo.uploader || '未知' }}</p>
              <p v-if="photo.description" class="description">{{ photo.description }}</p>
            </div>
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
          <p class="uploader">上传者：{{ modalPhoto.uploader || '未知' }}</p>
          <p v-if="modalPhoto.description">{{ modalPhoto.description }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import MultiSelectFilter from '../components/MultiSelectFilter.vue'

export default {
  components: { MultiSelectFilter },
  setup() {
    const photos = ref([])
    const years = ref([])
    const uploaders = ref([])
    const selectedYears = ref([])
    const selectedUploaders = ref([])
    const loading = ref(true)
    const modalPhoto = ref(null)

    // 年份/上传者转成通用筛选组件的选项格式
    const yearOptions = computed(() =>
      [...years.value].sort((a, b) => b - a).map(y => ({ value: y, label: `${y} 年` }))
    )
    const uploaderOptions = computed(() =>
      uploaders.value.map(u => ({ value: u.id, label: u.username }))
    )

    // 按年份分组照片 - 使用数组保证排序正确
    const groupedPhotos = computed(() => {
      const grouped = {}
      photos.value.forEach(photo => {
        const year = parseInt(photo.shoot_date.substring(0, 4), 10)
        if (!grouped[year]) {
          grouped[year] = []
        }
        grouped[year].push(photo)
      })
      // 转换为数组并按年份降序排列（转换为数字比较）
      return Object.keys(grouped)
        .map(key => ({ year: Number(key), photos: grouped[key] }))
        .sort((a, b) => b.year - a.year)
    })

    onMounted(async () => {
      await loadYears()
      await loadUploaders()
      await loadPhotos()
    })

    const loadYears = async () => {
      try {
        const response = await axios.get('/api/years')
        years.value = response.data
        // 默认不选中，不选中时返回全部照片
        selectedYears.value = []
      } catch (error) {
        console.error('Failed to load years', error)
      }
    }

    const loadUploaders = async () => {
      try {
        const response = await axios.get('/api/uploaders')
        uploaders.value = response.data
        selectedUploaders.value = []
      } catch (error) {
        console.error('Failed to load uploaders', error)
      }
    }

    const loadPhotos = async () => {
      loading.value = true
      try {
        const params = []
        selectedYears.value.forEach(year => params.push(`year=${year}`))
        selectedUploaders.value.forEach(uid => params.push(`uploader=${uid}`))
        let url = '/api/photos'
        if (params.length > 0) {
          url += `?${params.join('&')}`
        }
        const response = await axios.get(url)
        photos.value = response.data
      } catch (error) {
        console.error('Failed to load photos', error)
      } finally {
        loading.value = false
      }
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
      photos,
      years,
      uploaders,
      selectedYears,
      selectedUploaders,
      yearOptions,
      uploaderOptions,
      groupedPhotos,
      loading,
      modalPhoto,
      loadPhotos,
      openModal,
      closeModal,
      getOriginalUrl
    }
  }
}
</script>

<style scoped>
.year-filter {
  margin-bottom: 2rem;
  padding: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  background-color: white;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.year-filter label {
  font-weight: bold;
}

.year-section {
  margin-bottom: 3rem;
}

.year-title {
  font-size: 1.5rem;
  color: #333;
  border-bottom: 2px solid #ddd;
  padding-bottom: 0.5rem;
  margin-bottom: 1.5rem;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.photo-card {
  overflow: hidden;
  transition: transform 0.2s;
}

.photo-card:hover {
  transform: translateY(-5px);
}

.photo-container {
  width: 100%;
  padding-top: 75%;
  position: relative;
  overflow: hidden;
  background-color: #f0f0f0;
}

.photo-container img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
}

.photo-info {
  padding: 1rem 0 0 0;
}

.photo-info h4 {
  margin: 0 0 0.5rem 0;
}

.date {
  color: #666;
  font-size: 0.9rem;
  margin: 0.25rem 0;
}

.uploader {
  color: #666;
  font-size: 0.9rem;
  margin: 0.25rem 0;
}

.description {
  color: #888;
  font-size: 0.85rem;
  margin: 0.5rem 0 0 0;
}

.original-link {
  margin: 0.75rem 0 0 0;
  padding: 0;
}

.original-link a {
  color: #007bff;
  text-decoration: none;
  font-size: 0.9rem;
}

.original-link a:hover {
  text-decoration: underline;
}

.original-link-inline a {
  color: #007bff;
  text-decoration: none;
  font-size: 0.9rem;
  margin-left: 1rem;
}

.original-link-inline a:hover {
  text-decoration: underline;
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

@media (max-width: 768px) {
  .photo-grid {
    grid-template-columns: 1fr;
  }
}
</style>
