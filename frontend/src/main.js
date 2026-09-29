import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

axios.defaults.baseURL = import.meta.env.BASE_URL

app.use(pinia)
app.use(router)
app.mount('#app')
