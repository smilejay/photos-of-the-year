<template>
  <div class="login-container">
    <div class="login-card card">
      <h2 class="text-center mb-2">Photos of the Year</h2>
      <h3 class="text-center mb-2">请登录</h3>

      <div v-if="error" class="error-message">{{ error }}</div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="username" type="text" required placeholder="请输入用户名">
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="password" type="password" required placeholder="请输入密码">
        </div>
        <button type="submit" class="btn btn-primary w-100" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

export default {
  setup() {
    const username = ref('')
    const password = ref('')
    const error = ref('')
    const loading = ref(false)
    const authStore = useAuthStore()
    const router = useRouter()

    const handleLogin = async () => {
      loading.value = true
      error.value = ''

      const result = await authStore.login(username.value, password.value)

      if (result.success) {
        router.push('/gallery')
      } else {
        error.value = result.message
      }

      loading.value = false
    }

    return {
      username,
      password,
      error,
      loading,
      handleLogin
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 100px);
}

.login-card {
  width: 100%;
  max-width: 400px;
}

.w-100 {
  width: 100%;
}

.btn-primary {
  background-color: #3498db;
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
}

.btn-primary:hover:not(:disabled) {
  background-color: #2980b9;
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>
