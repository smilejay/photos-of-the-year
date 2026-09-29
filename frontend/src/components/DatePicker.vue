<template>
  <div class="date-picker" :class="{ open }">
    <div class="dp-trigger" @click="toggle">
      <input
        class="dp-input"
        type="text"
        readonly
        :value="modelValue"
        :placeholder="placeholder"
      >
      <span class="dp-icon">📅</span>
    </div>

    <div v-if="open" class="dp-panel">
      <!-- 头部导航 -->
      <div class="dp-header">
        <button type="button" class="dp-nav" @click="prev">‹</button>
        <div class="dp-selectors">
          <select v-model.number="viewYear" class="dp-select" aria-label="选择年份">
            <option v-for="year in yearOptions" :key="year" :value="year">
              {{ year }}年
            </option>
          </select>
          <select v-model.number="viewMonth" class="dp-select" aria-label="选择月份">
            <option v-for="month in monthOptions" :key="month.value" :value="month.value">
              {{ month.label }}
            </option>
          </select>
        </div>
        <button type="button" class="dp-nav" @click="next">›</button>
      </div>

      <div class="dp-body">
        <div class="dp-weekdays">
          <span v-for="w in weekdays" :key="w">{{ w }}</span>
        </div>
        <div class="dp-days">
          <button
            v-for="(cell, i) in dayCells"
            :key="i"
            type="button"
            class="dp-day"
            :class="{ 'is-other': !cell.current, 'is-today': cell.isToday, 'is-selected': cell.isSelected }"
            @click="selectDay(cell)"
          >{{ cell.day }}</button>
        </div>
      </div>

      <!-- 底部快捷 -->
      <div class="dp-footer">
        <button type="button" class="dp-link" @click="selectToday">今天</button>
        <button type="button" class="dp-link" @click="clear">清除</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

export default {
  name: 'DatePicker',
  props: {
    modelValue: { type: String, default: '' },
    placeholder: { type: String, default: '请选择日期' }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const open = ref(false)
    const today = new Date()

    // 当前面板展示的年月（不等于选中值，仅用于翻页）
    const viewYear = ref(today.getFullYear())
    const viewMonth = ref(today.getMonth())

    const weekdays = ['日', '一', '二', '三', '四', '五', '六']
    const monthOptions = Array.from({ length: 12 }, (_, i) => ({
      value: i,
      label: `${i + 1}月`
    }))

    // 把 'YYYY-MM-DD' 解析为本地日期各部分，避免时区偏移
    const parseValue = (str) => {
      if (!str || !/^\d{4}-\d{2}-\d{2}$/.test(str)) return null
      const [y, m, d] = str.split('-').map(Number)
      return { y, m: m - 1, d }
    }

    // 打开时把面板定位到选中值所在的年月
    const syncView = () => {
      const parsed = parseValue(props.modelValue)
      if (parsed) {
        viewYear.value = parsed.y
        viewMonth.value = parsed.m
      } else {
        viewYear.value = today.getFullYear()
        viewMonth.value = today.getMonth()
      }
    }

    watch(() => props.modelValue, syncView)

    const pad = (n) => String(n).padStart(2, '0')
    const toStr = (y, m, d) => `${y}-${pad(m + 1)}-${pad(d)}`

    // 日视图的 42 个格子（含上下月补齐）
    const dayCells = computed(() => {
      const first = new Date(viewYear.value, viewMonth.value, 1)
      const startWeekday = first.getDay()
      const daysInMonth = new Date(viewYear.value, viewMonth.value + 1, 0).getDate()
      const prevDays = new Date(viewYear.value, viewMonth.value, 0).getDate()
      const selected = parseValue(props.modelValue)
      const cells = []

      for (let i = 0; i < 42; i++) {
        let y = viewYear.value
        let m = viewMonth.value
        let day
        let current = true
        if (i < startWeekday) {
          day = prevDays - startWeekday + 1 + i
          m -= 1
          if (m < 0) { m = 11; y -= 1 }
          current = false
        } else if (i >= startWeekday + daysInMonth) {
          day = i - startWeekday - daysInMonth + 1
          m += 1
          if (m > 11) { m = 0; y += 1 }
          current = false
        } else {
          day = i - startWeekday + 1
        }
        const isToday = y === today.getFullYear() && m === today.getMonth() && day === today.getDate()
        const isSelected = !!selected && selected.y === y && selected.m === m && selected.d === day
        cells.push({ y, m, day, current, isToday, isSelected })
      }
      return cells
    })

    // 拍摄年份通常为历史年份，提供 1900 至今年的直接下拉选择。
    const yearOptions = computed(() => {
      const maxYear = Math.max(today.getFullYear(), viewYear.value)
      const minYear = Math.min(1900, viewYear.value)
      return Array.from(
        { length: maxYear - minYear + 1 },
        (_, i) => maxYear - i
      )
    })

    const toggle = () => {
      if (!open.value) syncView()
      open.value = !open.value
    }

    const prev = () => {
      if (viewMonth.value === 0) {
        viewMonth.value = 11
        viewYear.value -= 1
      } else {
        viewMonth.value -= 1
      }
    }

    const next = () => {
      if (viewMonth.value === 11) {
        viewMonth.value = 0
        viewYear.value += 1
      } else {
        viewMonth.value += 1
      }
    }

    const selectDay = (cell) => {
      emit('update:modelValue', toStr(cell.y, cell.m, cell.day))
      open.value = false
    }

    const selectToday = () => {
      emit('update:modelValue', toStr(today.getFullYear(), today.getMonth(), today.getDate()))
      open.value = false
    }

    const clear = () => {
      emit('update:modelValue', '')
      open.value = false
    }

    const handleClickOutside = (e) => {
      if (!e.target.closest('.date-picker')) open.value = false
    }
    onMounted(() => document.addEventListener('click', handleClickOutside))
    onUnmounted(() => document.removeEventListener('click', handleClickOutside))

    return {
      open, viewYear, viewMonth, weekdays, monthOptions,
      dayCells, yearOptions, toggle, prev, next,
      selectDay, selectToday, clear
    }
  }
}
</script>

<style scoped>
.date-picker {
  position: relative;
  width: 100%;
}

.dp-trigger {
  display: flex;
  align-items: center;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s;
}

.dp-trigger:hover {
  border-color: #3498db;
}

.date-picker.open .dp-trigger {
  border-color: #3498db;
}

.dp-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  padding: 0.5rem;
  cursor: pointer;
  min-width: 0;
}

.dp-icon {
  padding: 0 0.6rem;
  font-size: 1rem;
  user-select: none;
}

.dp-panel {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 200;
  width: 280px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
  padding: 0.75rem;
  user-select: none;
}

.dp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.dp-nav {
  border: none;
  background: transparent;
  font-size: 1.3rem;
  line-height: 1;
  color: #555;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.dp-nav:hover {
  background: #f0f0f0;
  color: #3498db;
}

.dp-selectors {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.dp-select {
  width: auto;
  min-width: 82px;
  height: 34px;
  border: 1px solid #d5dbe1;
  border-radius: 4px;
  background: white;
  color: #333;
  font-size: 0.9rem;
  padding: 0 1.6rem 0 0.45rem;
  cursor: pointer;
}

.dp-select:hover,
.dp-select:focus {
  border-color: #3498db;
  outline: none;
}

.dp-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  margin-bottom: 0.25rem;
}

.dp-weekdays span {
  text-align: center;
  font-size: 0.8rem;
  color: #999;
  padding: 0.25rem 0;
}

.dp-days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.dp-day {
  border: none;
  background: transparent;
  aspect-ratio: 1;
  border-radius: 50%;
  font-size: 0.9rem;
  color: #333;
}

.dp-day:hover {
  background: #eaf4fc;
}

.dp-day.is-other {
  color: #ccc;
}

.dp-day.is-today {
  color: #3498db;
  font-weight: bold;
}

.dp-day.is-selected {
  background: #3498db;
  color: white;
  font-weight: bold;
}

.dp-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid #eee;
}

.dp-link {
  border: none;
  background: transparent;
  color: #3498db;
  font-size: 0.85rem;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
}

.dp-link:hover {
  background: #eaf4fc;
}
</style>
