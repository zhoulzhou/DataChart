import { createApp } from 'vue'
import router from './router'
import App from './App.vue'
import Toast from './components/Toast.vue'
import './assets/style.css'

const app = createApp(App)
app.use(router)
app.component('Toast', Toast)
app.mount('#app')
