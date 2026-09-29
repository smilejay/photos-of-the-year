<template>
  <div id="app">
    <nav v-if="isAuthenticated" class="navbar">
      <div class="container">
        <h1 class="logo">Photos of the Year 年度照片</h1>
        <div class="nav-links">
          <router-link to="/gallery">相册展示</router-link>
          <router-link to="/admin">相册管理</router-link>
          <router-link to="/users" v-if="isAdmin">用户管理</router-link>
          <span class="username">{{ username }}</span>
          <a href="#" @click.prevent="logout" class="logout-link">退出</a>
        </div>
      </div>
    </nav>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script>
import { computed } from 'vue'
import { useAuthStore } from './stores/auth'

export default {
  setup() {
    const authStore = useAuthStore()
    const isAuthenticated = computed(() => authStore.isAuthenticated)
    const isAdmin = computed(() => authStore.isAdmin)
    const username = computed(() => authStore.user?.username || '')

    const logout = async () => {
      await authStore.logout()
    }

    return {
      isAuthenticated,
      isAdmin,
      username,
      logout
    }
  }
}
</script>

<style>
#app {
  min-height: 100vh;
  background-color: #f5f5f5;
}

.navbar {
  background-color: #2c3e50;
  color: white;
  padding: 1rem 0;
}

.navbar .container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  margin: 0;
  font-size: 1.5rem;
}

.nav-links {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.nav-links a,
.nav-links router-link,
.nav-links span {
  color: white;
  text-decoration: none;
  transition: opacity 0.2s;
  font-size: 1.5em;
}

.username {
  color: #ccc;
  font-size: 1.5em;
}

.nav-links a:hover,
.nav-links router-link:hover {
  opacity: 0.8;
}

/* 当前所在页面的导航高亮（router-link 激活时自动带 router-link-active）*/
.nav-links a.router-link-active {
  opacity: 1;
  color: #2c3e50;
  background-color: #d6ecff;
  border-radius: 6px;
  padding: 0.15rem 0.7rem;
  font-weight: bold;
}

.logout-link {
  cursor: pointer;
}

.username {
  color: #ccc;
}

main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}
</style>
