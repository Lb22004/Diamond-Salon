<script setup>
import { computed, ref } from 'vue'
import { MONTH_SHORT_ES } from '@/utils/months'

const props = defineProps({
  year: {
    type: Number,
    required: true,
  },
  /** Periods belonging to `year` (any order). Months without a period render as unavailable. */
  periods: {
    type: Array,
    default: () => [],
  },
  /** 'pick' = choose one existing period · 'multi' = toggle months (e.g. to generate them). */
  mode: {
    type: String,
    default: 'pick',
  },
  /** Selected period id (pick mode). */
  selectedId: {
    type: Number,
    default: null,
  },
  /** Selected month numbers (multi mode, v-model). */
  modelValue: {
    type: Array,
    default: () => [],
  },
  /** Months that cannot be toggled in multi mode (e.g. already generated). */
  lockedMonths: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['select', 'update:modelValue'])
const gridRef = ref(null)

const cells = computed(() => {
  const byMonth = Object.fromEntries(props.periods.map((p) => [p.month, p]))
  return MONTH_SHORT_ES.map((short, idx) => {
    const month = idx + 1
    const period = byMonth[month] || null
    if (props.mode === 'multi') {
      const locked = props.lockedMonths.includes(month)
      return {
        month,
        short,
        period,
        disabled: locked,
        locked,
        selected: locked || props.modelValue.includes(month),
      }
    }
    return {
      month,
      short,
      period,
      disabled: !period,
      locked: false,
      selected: Boolean(period && period.id === props.selectedId),
    }
  })
})

function cellTitle(cell) {
  if (props.mode === 'multi') {
    return cell.locked ? 'Ya generado' : cell.selected ? 'Seleccionado para generar' : 'Clic para seleccionar'
  }
  if (!cell.period) return 'Período no disponible'
  const status = cell.period.status === 'OPEN' ? 'Abierto' : 'Cerrado'
  return `${cell.period.label} · ${status}${cell.period.is_active ? ' · Activo por defecto' : ''}`
}

function onClick(cell) {
  if (cell.disabled) return
  if (props.mode === 'multi') {
    const set = new Set(props.modelValue)
    if (set.has(cell.month)) set.delete(cell.month)
    else set.add(cell.month)
    emit(
      'update:modelValue',
      [...set].sort((a, b) => a - b)
    )
    return
  }
  emit('select', cell.period)
}

/** Arrow-key navigation across the 4x3 grid, skipping unavailable months. */
function onKeydown(event) {
  const deltas = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -4, ArrowDown: 4 }
  const delta = deltas[event.key]
  if (!delta) return
  const buttons = Array.from(gridRef.value?.querySelectorAll('button') || [])
  const current = buttons.indexOf(document.activeElement)
  if (current === -1) return
  event.preventDefault()
  let next = current + delta
  while (next >= 0 && next < buttons.length) {
    if (!buttons[next].disabled) {
      buttons[next].focus()
      return
    }
    next += delta
  }
}

function focusSelected() {
  const buttons = Array.from(gridRef.value?.querySelectorAll('button') || [])
  const target = buttons.find((b) => b.classList.contains('is-selected') && !b.disabled) || buttons.find((b) => !b.disabled)
  target?.focus()
}

defineExpose({ focusSelected })
</script>

<template>
  <div
    ref="gridRef"
    class="ds-month-grid"
    :class="`ds-month-grid--${mode}`"
    role="grid"
    :aria-label="`Meses de ${year}`"
    @keydown="onKeydown"
  >
    <button
      v-for="cell in cells"
      :key="cell.month"
      type="button"
      class="ds-month-grid__cell"
      :class="{
        'is-selected': cell.selected,
        'is-closed': cell.period?.status === 'CLOSED',
        'is-active': cell.period?.is_active,
        'is-hidden': cell.period?.is_hidden,
        'is-locked': cell.locked,
        'is-empty': !cell.period,
      }"
      :disabled="cell.disabled"
      :title="cellTitle(cell)"
      :aria-pressed="cell.selected"
      @click="onClick(cell)"
    >
      <span class="ds-month-grid__label">{{ cell.short }}</span>
      <span v-if="cell.period?.status === 'CLOSED'" class="ds-month-grid__icon" aria-hidden="true">🔒</span>
      <span v-else-if="cell.period?.is_active" class="ds-month-grid__dot" aria-hidden="true" />
    </button>
  </div>
</template>
