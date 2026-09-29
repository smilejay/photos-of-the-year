<template>
  <div class="multi-select" :class="{ open: dropdownOpen }">
    <div class="select-trigger" @click="openDropdown">
      <input
        class="filter-input"
        type="text"
        v-model="filterText"
        :placeholder="triggerPlaceholder"
        @focus="openDropdown"
        @input="openDropdown"
      >
      <span class="arrow" @click.stop="toggleDropdown">▼</span>
    </div>
    <div v-if="dropdownOpen" class="dropdown-menu">
      <label class="dropdown-item" v-for="opt in filteredOptions" :key="opt.value">
        <input type="checkbox" :value="opt.value" :checked="modelValue.includes(opt.value)" @change="toggleOption(opt.value)">
        <span>{{ opt.label }}</span>
      </label>
      <div v-if="filteredOptions.length === 0" class="dropdown-empty">
        无匹配{{ noun }}
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'

export default {
  name: 'MultiSelectFilter',
  props: {
    // v-model: 选中的值数组
    modelValue: {
      type: Array,
      default: () => []
    },
    // 选项列表：[{ value, label }]
    options: {
      type: Array,
      default: () => []
    },
    // 名词，用于占位符/空态文案，如“年份”“上传者”
    noun: {
      type: String,
      default: '选项'
    }
  },
  emits: ['update:modelValue', 'change'],
  setup(props, { emit }) {
    const dropdownOpen = ref(false)
    const filterText = ref('')

    const filteredOptions = computed(() => {
      const q = filterText.value.trim().toLowerCase()
      if (!q) return props.options
      return props.options.filter(o => String(o.label).toLowerCase().includes(q))
    })

    const triggerPlaceholder = computed(() => {
      if (dropdownOpen.value) return `输入${props.noun}筛选`
      if (props.modelValue.length === 0) return `请选择${props.noun}（可搜索）`
      return `${props.modelValue.length} 个${props.noun}已选`
    })

    const openDropdown = () => {
      dropdownOpen.value = true
    }

    const toggleDropdown = () => {
      dropdownOpen.value = !dropdownOpen.value
      if (!dropdownOpen.value) filterText.value = ''
    }

    const toggleOption = (value) => {
      const next = props.modelValue.includes(value)
        ? props.modelValue.filter(v => v !== value)
        : [...props.modelValue, value]
      emit('update:modelValue', next)
      emit('change', next)
    }

    // Click outside to close
    const handleClickOutside = (e) => {
      if (!e.target.closest('.multi-select')) {
        dropdownOpen.value = false
        filterText.value = ''
      }
    }

    onMounted(() => {
      document.addEventListener('click', handleClickOutside)
    })

    onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside)
    })

    return {
      dropdownOpen,
      filterText,
      filteredOptions,
      triggerPlaceholder,
      openDropdown,
      toggleDropdown,
      toggleOption
    }
  }
}
</script>

<style scoped>
.multi-select {
  position: relative;
  display: inline-block;
  width: 240px;
}

.select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.25rem 0.75rem 0.25rem 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  cursor: text;
  min-height: 38px;
  gap: 0.5rem;
}

.select-trigger:hover {
  border-color: #999;
}

.filter-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.95rem;
  padding: 0.25rem 0.25rem;
  min-width: 0;
}

.filter-input::placeholder {
  color: #999;
}

.arrow {
  font-size: 0.7rem;
  color: #999;
  transition: transform 0.2s;
  cursor: pointer;
  flex-shrink: 0;
}

.multi-select.open .arrow {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 300px;
  overflow-y: auto;
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 100;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  margin: 0;
}

.dropdown-item:hover {
  background-color: #f5f5f5;
}

.dropdown-item input {
  margin: 0;
}

.dropdown-empty {
  padding: 0.75rem;
  text-align: center;
  color: #999;
  font-size: 0.9rem;
}
</style>
