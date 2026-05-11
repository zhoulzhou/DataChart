<script setup>
import { ref, watch } from 'vue'

const toasts = ref([])
let id = 0

function addToast(message, type = 'info', duration = 3000) {
  const t = { id: ++id, message, type, leaving: false }
  toasts.value.push(t)
  setTimeout(() => {
    t.leaving = true
    setTimeout(() => {
      toasts.value = toasts.value.filter(item => item.id !== t.id)
    }, 300)
  }, duration)
}

function toast(message, type) {
  addToast(message, type)
}

if (typeof window !== 'undefined') {
  window.$toast = { success: m => toast(m, 'success'), error: m => toast(m, 'error'), info: m => toast(m, 'info') }
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="toast-item"
        :class="[`toast-${t.type}`, { 'toast-leaving': t.leaving }]"
      >{{ t.message }}</div>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}
.toast-item {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  animation: toast-in 0.3s ease;
  pointer-events: auto;
}
.toast-success { background: #2ecc71; }
.toast-error { background: #e74c3c; }
.toast-info { background: #3498db; }
.toast-leaving { animation: toast-out 0.3s ease forwards; }

@keyframes toast-in {
  from { opacity: 0; transform: translateX(50px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes toast-out {
  from { opacity: 1; transform: translateX(0); }
  to { opacity: 0; transform: translateX(50px); }
}
</style>