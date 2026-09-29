<template>
  <div>
    <h2 class="mb-2">用户管理</h2>

    <div class="add-user card mb-2">
      <h3>添加新用户</h3>
      <form @submit.prevent="handleAddUser">
        <div class="form-row">
          <div class="form-group">
            <label>用户名 *</label>
            <input v-model="newUser.username" type="text" required placeholder="输入用户名">
          </div>
          <div class="form-group">
            <label>密码 *</label>
            <input v-model="newUser.password" type="password" required placeholder="输入密码">
          </div>
          <div class="form-group">
            <label>用户类型</label>
            <label class="checkbox-label">
              <input v-model="newUser.is_admin" type="checkbox">
	      管理员
	    </label>
          </div>
        </div>
        <div v-if="addError" class="error-message">{{ addError }}</div>
        <div v-if="addSuccess" class="success-message">{{ addSuccess }}</div>
        <button type="submit" class="btn btn-success" :disabled="adding">
          {{ adding ? '添加中...' : '添加用户' }}
        </button>
      </form>
    </div>

    <div class="user-list">
      <h3>用户列表</h3>
      <div v-if="loading" class="text-center mt-2">
        <p>加载中...</p>
      </div>
      <div v-else>
        <div v-for="user in users" :key="user.id" class="user-item card">
          <div class="user-info">
            <div class="user-name">
              <strong>{{ user.username }}</strong>
              <span :class="['badge', user.is_admin ? 'badge-admin' : 'badge-user']">
                {{ user.is_admin ? '管理员' : '普通用户' }}
              </span>
            </div>
          </div>
          <div class="user-actions">
            <button class="btn btn-primary" @click="editUser(user)">编辑</button>
            <button class="btn btn-danger" @click="deleteUser(user)" :disabled="user.id === currentUserId">
              删除
            </button>
          </div>
        </div>

        <div v-if="users.length === 0" class="empty-state text-center mt-2">
          <p>暂无用户</p>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="editingUser" class="modal" @click.self="cancelEdit">
      <div class="modal-content card">
        <h3>编辑用户</h3>
        <form @submit.prevent="handleUpdateUser">
          <div class="form-group">
            <label>用户名 *</label>
            <input v-model="editingUser.username" type="text" required>
          </div>
          <div class="form-group">
            <label>新密码（留空则不修改）</label>
            <input v-model="editingForm.password" type="password" placeholder="输入新密码">
          </div>
          <div class="form-group">
            <label>用户类型</label>
            <label class="checkbox-label">
              <input v-model="editingUser.is_admin" type="checkbox">
              管理员
            </label>
          </div>
          <div v-if="editError" class="error-message">{{ editError }}</div>
          <div class="form-actions">
            <button type="button" class="btn btn-secondary" @click="cancelEdit">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="updating">保存修改</button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!pendingDeleteUser"
      title="删除用户"
      :message="pendingDeleteUser ? `确定要删除用户 “${pendingDeleteUser.username}” 吗？此操作不可恢复。` : ''"
      confirm-text="删除"
      danger
      @confirm="confirmDelete"
      @cancel="pendingDeleteUser = null"
    />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import ConfirmDialog from '../components/ConfirmDialog.vue'

export default {
  components: { ConfirmDialog },
  setup() {
    const authStore = useAuthStore()
    const users = ref([])
    const loading = ref(true)
    const adding = ref(false)
    const addError = ref('')
    const addSuccess = ref('')

    const newUser = ref({
      username: '',
      password: '',
      is_admin: false
    })

    const editingUser = ref(null)
    const editingForm = ref({
      password: ''
    })

    const currentUserId = ref(authStore.user?.id)

    const editError = ref('')
    const updating = ref(false)
    const pendingDeleteUser = ref(null)

    const loadUsers = async () => {
      loading.value = true
      try {
        const response = await axios.get('/api/users')
        users.value = response.data
      } catch (error) {
        console.error('Failed to load users', error)
      } finally {
        loading.value = false
      }
    }

    const handleAddUser = async () => {
      adding.value = true
      addError.value = ''
      addSuccess.value = ''

      try {
        await axios.post('/api/users', {
          username: newUser.value.username,
          password: newUser.value.password,
          is_admin: newUser.value.is_admin
        })

        addSuccess.value = '用户添加成功'
        newUser.value = {
          username: '',
          password: '',
          is_admin: false
        }
        loadUsers()
      } catch (error) {
        addError.value = error.response?.data?.message || '添加失败'
      } finally {
        adding.value = false
      }
    }

    const editUser = (user) => {
      editingUser.value = { ...user }
      editingForm.value = {
        password: ''
      }
      editError.value = ''
    }

    const cancelEdit = () => {
      editingUser.value = null
      editingForm.value = { password: '' }
      editError.value = ''
    }

    const handleUpdateUser = async () => {
      updating.value = true
      editError.value = ''

      try {
        const data = {
          username: editingUser.value.username,
          is_admin: editingUser.value.is_admin
        }

        if (editingForm.value.password) {
          data.password = editingForm.value.password
        }

        await axios.put(`/api/users/${editingUser.value.id}`, data)
        await loadUsers()
        cancelEdit()
        addSuccess.value = '用户信息已更新'
        setTimeout(() => addSuccess.value = '', 3000)
      } catch (error) {
        editError.value = error.response?.data?.message || '更新失败'
      } finally {
        updating.value = false
      }
    }

    const deleteUser = (user) => {
      pendingDeleteUser.value = user
    }

    const confirmDelete = async () => {
      const user = pendingDeleteUser.value
      pendingDeleteUser.value = null
      if (!user) return
      try {
        await axios.delete(`/api/users/${user.id}`)
        await loadUsers()
        addSuccess.value = '用户已删除'
        setTimeout(() => addSuccess.value = '', 3000)
      } catch (error) {
        addError.value = error.response?.data?.message || '删除失败'
      }
    }

    onMounted(() => {
      loadUsers()
    })

    return {
      users,
      loading,
      adding,
      addError,
      addSuccess,
      newUser,
      editingUser,
      editingForm,
      editError,
      updating,
      currentUserId,
      pendingDeleteUser,
      loadUsers,
      handleAddUser,
      editUser,
      cancelEdit,
      handleUpdateUser,
      deleteUser,
      confirmDelete
    }
  }
}
</script>

<style scoped>
.add-user {
  padding: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr 200px;
  gap: 1rem;
  align-items: end;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  white-space: nowrap;
}

.checkbox-label input[type="checkbox"] {
  margin: 0;
  margin-right: 0.5rem;
}

.user-list {
  margin-top: 2rem;
}

.user-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  margin-bottom: 1rem;
}

.user-name {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8rem;
}

.badge-admin {
  background-color: #e74c3c;
  color: white;
}

.badge-user {
  background-color: #3498db;
  color: white;
}

.user-actions {
  display: flex;
  gap: 0.5rem;
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
  background-color: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  width: 100%;
  max-width: 500px;
  margin: 2rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1.5rem;
}

@media (max-width: 600px) {
  .user-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
