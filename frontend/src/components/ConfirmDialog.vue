<template>
  <div v-if="visible" class="confirm-overlay" @click.self="onCancel">
    <div class="confirm-box card">
      <h3 class="confirm-title">{{ title }}</h3>
      <p class="confirm-message">{{ message }}</p>
      <div class="confirm-actions">
        <button class="btn btn-secondary" @click="onCancel">{{ cancelText }}</button>
        <button class="btn" :class="dangerClass" @click="onConfirm">{{ confirmText }}</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConfirmDialog',
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: '确认操作' },
    message: { type: String, default: '' },
    confirmText: { type: String, default: '确定' },
    cancelText: { type: String, default: '取消' },
    danger: { type: Boolean, default: false }
  },
  emits: ['confirm', 'cancel'],
  computed: {
    dangerClass() {
      return this.danger ? 'btn-danger' : 'btn-primary'
    }
  },
  methods: {
    onConfirm() {
      this.$emit('confirm')
    },
    onCancel() {
      this.$emit('cancel')
    }
  }
}
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  padding: 1rem;
}

.confirm-box {
  width: 100%;
  max-width: 420px;
  margin: 0;
}

.confirm-title {
  margin: 0 0 0.75rem 0;
}

.confirm-message {
  margin: 0 0 1.5rem 0;
  color: #555;
  white-space: pre-line;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.btn-primary {
  background-color: #3498db;
}

.btn-primary:hover {
  background-color: #2980b9;
}
</style>
