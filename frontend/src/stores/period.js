import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import http from '@/api/http'

const FALLBACK_PERIOD = {
  id: 11,
  year: 2026,
  month: 11,
  month_name: 'Noviembre',
  label: 'Noviembre 2026',
  code: '11/2026',
  start_date: '2026-11-01',
  end_date: '2026-11-30',
  status: 'OPEN',
  status_label: 'Abierto',
  is_active: true,
}

export const usePeriodStore = defineStore('period', () => {
  const periods = ref([])
  const selectedPeriodId = ref(Number(localStorage.getItem('selected_period_id')) || null)
  const loading = ref(false)

  const activePeriod = computed(() => {
    if (selectedPeriodId.value) {
      const found = periods.value.find((p) => p.id === selectedPeriodId.value)
      if (found) return found
    }
    return (
      periods.value.find((p) => p.is_active) ||
      periods.value[0] ||
      FALLBACK_PERIOD
    )
  })

  const periodLabel = computed(() => activePeriod.value?.label || 'Noviembre 2026')
  const isPeriodOpen = computed(() => activePeriod.value?.status === 'OPEN')

  async function fetchPeriods() {
    loading.value = true
    try {
      const { data } = await http.get('/v1/periods/')
      const list = Array.isArray(data) ? data : data.results || []
      periods.value = list
      if (!selectedPeriodId.value || !list.some((p) => p.id === selectedPeriodId.value)) {
        const defaultActive = list.find((p) => p.is_active) || list.find((p) => p.year === 2026 && p.month === 11) || list[0]
        if (defaultActive) {
          selectedPeriodId.value = defaultActive.id
          localStorage.setItem('selected_period_id', String(defaultActive.id))
        }
      }
      return list
    } catch {
      if (periods.value.length === 0) {
        periods.value = [FALLBACK_PERIOD]
      }
      return periods.value
    } finally {
      loading.value = false
    }
  }

  function selectPeriod(periodId) {
    const idNum = Number(periodId)
    selectedPeriodId.value = idNum
    localStorage.setItem('selected_period_id', String(idNum))
  }

  async function activateServerPeriod(periodId) {
    const { data } = await http.post(`/v1/periods/${periodId}/activate/`)
    await fetchPeriods()
    selectPeriod(data.id)
    return data
  }

  async function reopenPeriod(periodId, reason) {
    const { data } = await http.post(`/v1/periods/${periodId}/reopen/`, { reason })
    await fetchPeriods()
    return data
  }

  async function generateYear(year) {
    const { data } = await http.post('/v1/periods/generate-year/', { year })
    await fetchPeriods()
    return data
  }

  return {
    periods,
    selectedPeriodId,
    loading,
    activePeriod,
    periodLabel,
    isPeriodOpen,
    fetchPeriods,
    selectPeriod,
    activateServerPeriod,
    reopenPeriod,
    generateYear,
  }
})
