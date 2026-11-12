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
  const periods = ref([]) // visible periods (header picker)
  const allPeriods = ref([]) // includes hidden periods (settings management)
  const fiscalYears = ref([])
  const managementLoaded = ref(false)
  const selectedPeriodId = ref(null)
  const userManuallySelected = ref(false)
  const loading = ref(false)

  /** Visible periods grouped by year: { 2026: [period, ...], ... } (months ascending). */
  const periodsByYear = computed(() => {
    const groups = {}
    for (const p of periods.value) {
      ;(groups[p.year] ||= []).push(p)
    }
    for (const year of Object.keys(groups)) {
      groups[year].sort((a, b) => a.month - b.month)
    }
    return groups
  })

  /** Years with at least one visible period, newest first. */
  const availableYears = computed(() =>
    Object.keys(periodsByYear.value)
      .map(Number)
      .sort((a, b) => b - a)
  )

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
      if (!userManuallySelected.value || !selectedPeriodId.value || !list.some((p) => p.id === selectedPeriodId.value)) {
        const defaultActive =
          list.find((p) => p.is_active) ||
          list.find((p) => p.year === 2026 && p.month === 11) ||
          list[0]
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
    userManuallySelected.value = true
    selectedPeriodId.value = idNum
    localStorage.setItem('selected_period_id', String(idNum))
  }

  async function activateServerPeriod(periodId) {
    const { data } = await http.post(`/v1/periods/${periodId}/activate/`)
    await refreshAll()
    selectPeriod(data.id)
    return data
  }

  async function reopenPeriod(periodId, reason) {
    const { data } = await http.post(`/v1/periods/${periodId}/reopen/`, { reason })
    await refreshAll()
    return data
  }

  async function generateYear(year) {
    return generatePeriods({ year, mode: 'FULL' })
  }

  /**
   * Generate periods for a fiscal year.
   * payload: { year, mode: 'FULL' | 'RANGE' | 'MONTHS', start_month?, end_month?, months? }
   */
  async function generatePeriods(payload) {
    const { data } = await http.post('/v1/periods/generate-year/', payload)
    await refreshAll()
    return data
  }

  async function generateNextPeriod() {
    const { data } = await http.post('/v1/periods/generate-next/')
    await refreshAll()
    return data
  }

  async function fetchAllPeriods() {
    const { data } = await http.get('/v1/periods/', { params: { include_hidden: true } })
    allPeriods.value = Array.isArray(data) ? data : data.results || []
    return allPeriods.value
  }

  async function fetchFiscalYears() {
    const { data } = await http.get('/v1/fiscal-years/')
    fiscalYears.value = Array.isArray(data) ? data : data.results || []
    return fiscalYears.value
  }

  /** Refresh the picker list, and the management lists if they were loaded. */
  async function refreshAll() {
    const tasks = [fetchPeriods()]
    if (managementLoaded.value) tasks.push(fetchAllPeriods(), fetchFiscalYears())
    await Promise.all(tasks)
  }

  async function loadManagement() {
    managementLoaded.value = true
    await Promise.all([fetchPeriods(), fetchAllPeriods(), fetchFiscalYears()])
  }

  async function setPeriodHidden(periodId, hidden) {
    const { data } = await http.post(`/v1/periods/${periodId}/${hidden ? 'hide' : 'show'}/`)
    await refreshAll()
    return data
  }

  async function setYearHidden(fiscalYearId, hidden) {
    const { data } = await http.post(`/v1/fiscal-years/${fiscalYearId}/${hidden ? 'hide' : 'show'}/`)
    await refreshAll()
    return data
  }

  async function fetchPeriodUsage(periodId) {
    const { data } = await http.get(`/v1/periods/${periodId}/usage/`)
    return data
  }

  async function deletePeriod(periodId, reason = '') {
    const { data } = await http.delete(`/v1/periods/${periodId}/`, { data: { reason } })
    if (selectedPeriodId.value === periodId) userManuallySelected.value = false
    await refreshAll()
    return data
  }

  async function deleteFiscalYear(fiscalYearId, reason = '') {
    const { data } = await http.delete(`/v1/fiscal-years/${fiscalYearId}/`, { data: { reason } })
    await refreshAll()
    return data
  }

  return {
    periods,
    allPeriods,
    fiscalYears,
    selectedPeriodId,
    loading,
    activePeriod,
    periodLabel,
    isPeriodOpen,
    periodsByYear,
    availableYears,
    fetchPeriods,
    fetchAllPeriods,
    fetchFiscalYears,
    loadManagement,
    selectPeriod,
    activateServerPeriod,
    reopenPeriod,
    generateYear,
    generatePeriods,
    generateNextPeriod,
    setPeriodHidden,
    setYearHidden,
    fetchPeriodUsage,
    deletePeriod,
    deleteFiscalYear,
  }
})
