<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { usePeriodStore } from '@/stores/period'
import Badge from './Badge.vue'
import MonthGrid from './MonthGrid.vue'

const periodStore = usePeriodStore()
const authStore = useAuthStore()

const open = ref(false)
const viewYear = ref(null)
const rootRef = ref(null)
const gridRef = ref(null)

const years = computed(() => periodStore.availableYears) // newest first
const yearIndex = computed(() => years.value.indexOf(viewYear.value))
const canGoOlder = computed(() => yearIndex.value > -1 && yearIndex.value < years.value.length - 1)
const canGoNewer = computed(() => yearIndex.value > 0)
const yearPeriods = computed(() => periodStore.periodsByYear[viewYear.value] || [])
const defaultPeriod = computed(() => periodStore.periods.find((p) => p.is_active) || null)
const canManage = computed(() => authStore.allowedViews.includes('configuracion'))

onMounted(() => {
  if (periodStore.periods.length === 0) {
    periodStore.fetchPeriods()
  }
  document.addEventListener('mousedown', onDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocumentClick)
})

watch(
  () => periodStore.activePeriod?.year,
  (year) => {
    if (!open.value && year) viewYear.value = year
  },
  { immediate: true }
)

function onDocumentClick(event) {
  if (open.value && rootRef.value && !rootRef.value.contains(event.target)) {
    open.value = false
  }
}

async function toggle() {
  open.value = !open.value
  if (open.value) {
    viewYear.value = years.value.includes(periodStore.activePeriod?.year)
      ? periodStore.activePeriod.year
      : years.value[0]
    await nextTick()
    gridRef.value?.focusSelected()
  }
}

function shiftYear(direction) {
  // years are newest-first: "older" = higher index
  const next = yearIndex.value + (direction === 'older' ? 1 : -1)
  if (next >= 0 && next < years.value.length) viewYear.value = years.value[next]
}

function choose(period) {
  periodStore.selectPeriod(period.id)
  open.value = false
}

function goToDefault() {
  if (defaultPeriod.value) choose(defaultPeriod.value)
}

function onKeydown(event) {
  if (event.key === 'Escape' && open.value) {
    open.value = false
    rootRef.value?.querySelector('.ds-period-picker__trigger')?.focus()
  }
}
</script>

<template>
  <div ref="rootRef" class="ds-period-picker" @keydown="onKeydown">
    <span class="ds-period-picker__prefix">Período:</span>
    <button
      type="button"
      class="ds-period-picker__trigger"
      aria-haspopup="dialog"
      :aria-expanded="open"
      aria-label="Seleccionar período contable"
      @click="toggle"
    >
      {{ periodStore.activePeriod?.label }}
      <span class="ds-period-picker__caret" aria-hidden="true">▾</span>
    </button>
    <Badge
      :variant="periodStore.isPeriodOpen ? 'OPEN' : 'CLOSED'"
      size="sm"
    >
      {{ periodStore.isPeriodOpen ? 'ABIERTO' : 'CERRADO' }}
    </Badge>

    <div v-if="open" class="ds-period-popover" role="dialog" aria-label="Selector de período">
      <div class="ds-period-popover__header">
        <button
          type="button"
          class="ds-period-popover__nav"
          :disabled="!canGoOlder"
          aria-label="Año anterior"
          @click="shiftYear('older')"
        >
          ◀
        </button>
        <span class="ds-period-popover__year">{{ viewYear }}</span>
        <button
          type="button"
          class="ds-period-popover__nav"
          :disabled="!canGoNewer"
          aria-label="Año siguiente"
          @click="shiftYear('newer')"
        >
          ▶
        </button>
      </div>

      <MonthGrid
        v-if="viewYear"
        ref="gridRef"
        :year="viewYear"
        :periods="yearPeriods"
        :selected-id="periodStore.activePeriod?.id"
        @select="choose"
      />
      <p v-else class="text-muted ds-period-popover__empty">No hay períodos disponibles.</p>

      <div class="ds-period-popover__legend">
        <span><span class="ds-month-grid__dot" /> Activo por defecto</span>
        <span>🔒 Cerrado</span>
      </div>

      <div class="ds-period-popover__footer">
        <button
          v-if="defaultPeriod"
          type="button"
          class="ds-btn-link"
          @click="goToDefault"
        >
          Ir al período activo
        </button>
        <RouterLink
          v-if="canManage"
          to="/configuracion?tab=periods"
          class="ds-btn-link"
          @click="open = false"
        >
          Gestionar períodos →
        </RouterLink>
      </div>
    </div>
  </div>
</template>
