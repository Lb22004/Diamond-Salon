<script setup>
import { onMounted } from 'vue'
import { usePeriodStore } from '@/stores/period'
import Badge from './Badge.vue'

const periodStore = usePeriodStore()

onMounted(() => {
  if (periodStore.periods.length === 0) {
    periodStore.fetchPeriods()
  }
})

function onChange(event) {
  periodStore.selectPeriod(Number(event.target.value))
}
</script>

<template>
  <div class="ds-period-picker">
    <span class="ds-period-picker__prefix">Período:</span>
    <select
      class="ds-period-picker__select"
      :value="periodStore.activePeriod?.id"
      aria-label="Seleccionar período contable"
      @change="onChange"
    >
      <option
        v-for="p in periodStore.periods"
        :key="p.id"
        :value="p.id"
      >
        {{ p.label }} ({{ p.status === 'OPEN' ? 'Abierto' : 'Cerrado' }})
      </option>
    </select>
    <Badge
      :variant="periodStore.isPeriodOpen ? 'OPEN' : 'CLOSED'"
      size="sm"
    >
      {{ periodStore.isPeriodOpen ? 'ABIERTO' : 'CERRADO' }}
    </Badge>
  </div>
</template>
