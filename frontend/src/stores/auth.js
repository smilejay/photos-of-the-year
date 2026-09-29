import { defineStore } from 'pinia'
import axios from 'axios'
import router from '../router'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    checkedAuth: false
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
    isAdmin: (state) => state.user?.is_admin || false
  },

  actions: {
    async login(username, password) {
      try {
        const response = await axios.post('/api/login', { username, password })
        if (response.data.success) {
          this.user = response.data.user
          return { success: true }
        }
        return { success: false, message: response.data.message }
      } catch (error) {
        return {
          success: false,
          message: error.response?.data?.message || '登录失败'
        }
      }
    },

    async logout() {
      await axios.post('/api/logout')
      this.user = null
      router.push('/login')
    },

    async checkAuth() {
      try {
        const response = await axios.get('/api/check-auth')
        if (response.data.authenticated) {
          this.user = response.data.user
        } else {
          this.user = null
        }
      } catch (error) {
        this.user = null
      } finally {
        this.checkedAuth = true
      }
    }
  }
})
