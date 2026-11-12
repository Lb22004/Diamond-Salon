<script setup>
import { computed, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import { formatDateLong } from '@/utils/formatters'
import { MONTH_NAMES_ES, MONTH_SHORT_ES, describeMonths } from '@/utils/months'

const props = defineProps({
  fiscalYear: {
    type: Object,
    required: true,
  },
  /** All periods (incl. hidden) of this fiscal year. */
  periods: {
    type: Array,
    default: () => [],
  },
  expanded: {
    type: Boolean,
    default: false,
  },
  isAdmin: {
    type: Boolean,
    default: false,
  },
  isAccountant: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'toggle',
  'activate',
  'set-hidden',
  'reopen',
  'delete',
  'add-months',
  'set-year-hidden',
  'delete-year',
])

const selectedMonth = ref(null)

const byMonth = computed(() => Object.fromEntries(props.periods.map((p) => [p.month, p])))
const tiles = computed(() =>
  MONTH_SHORT_ES.map((short, idx) => ({
    month: idx + 1,
    short,
    period: byMonth.value[idx + 1] || null,
  }))
)
const selectedPeriod = computed(() => (selectedMonth.value ? byMonth.value[selectedMonth.value] : null))

const generatedCount = computed(() => props.periods.length)
const hiddenCount = computed(() => props.periods.filter((p) => p.is_hidden).length)
const closedCount = computed(() => props.periods.filter((p) => p.status === 'CLOSED').length)
const allHidden = computed(() => generatedCount.value > 0 && props.periods.every((p) => p.is_hidden || p.is_active) && hiddenCount.value > 0)
const hasActive = computed(() => props.periods.some((p) => p.is_active))
const missingMonths = computed(() => tiles.value.filter((t) => !t.period).map((t) => t.month))

function onTileClick(tile) {
  if (!tile.period) {
    if (props.isAdmin) emit('add-months', { year: props.fiscalYear.year, months: [tile.month] })
    return
  }
  selectedMonth.value = selectedMonth.value === tile.month ? null : tile.month
}

function tileTitle(tile) {
  if (!tile.period) return props.isAdmin ? `Generar ${MONTH_NAMES_ES[tile.month - 1]} ${props.fiscalYear.year}` : 'No generado'
  return `${tile.period.label} · ${tile.period.status_label}`
}

const deleteYearTitle = computed(() => {
  if (props.fiscalYear.can_delete) return 'Eliminar el ejercicio y todos sus meses (sin datos registrados)'
  return 'No se puede eliminar: hay meses cerrados o con datos registrados'
})

const deletePeriodTitle = computed(() => {
  const p = selectedPeriod.value
  if (!p) return ''
  if (p.status === 'CLOSED') return 'Un período cerrado no puede eliminarse'
  if (p.has_data) return 'El período tiene datos registrados (partidas, ventas, compras o inventario)'
  return 'Eliminar este período vacío'
})
</script>

<template>
  <article class="ds-fy-card" :class="{ 'is-expanded': expanded, 'is-archived': allHidden }">
    <header class="ds-fy-card__header">
      <button type="button" class="ds-fy-card__toggle" :aria-expanded="expanded" @click="emit('toggle')">
        <span class="ds-fy-card__chevron" aria-hidden="true">{{ expanded ? '▾' : '▸' }}</span>
        <span class="ds-fy-card__title">Ejercicio {{ fiscalYear.year }}</span>
        <Badge :variant="fiscalYear.status" size="sm">{{ fiscalYear.status_label }}</Badge>
        <span class="ds-fy-card__meta">
          {{ generatedCount }}/12 meses
          <template v-if="closedCount"> · {{ closedCount }} cerrado(s)</template>
          <template v-if="hiddenCount"> · {{ hiddenCount }} oculto(s)</template>
        </span>
        <Badge v-if="hasActive" variant="gold" size="sm">ACTIVO</Badge>
      </button>

      <div class="ds-row-actions">
        <button
          v-if="isAdmin && missingMonths.length"
          type="button"
          class="ds-btn ds-btn--sm ds-btn--outline"
          :title="`Meses faltantes: ${describeMonths(missingMonths)}`"
          @click="emit('add-months', { year: fiscalYear.year, months: [] })"
        >
          + Agregar meses
        </button>
        <button
          v-if="isAccountant"
          type="button"
          class="ds-btn ds-btn--sm ds-btn--ghost"
          :title="allHidden ? 'Mostrar todos los meses en el selector' : 'Ocultar todos los meses del selector (excepto el activo)'"
          @click="emit('set-year-hidden', { fiscalYear, hidden: !allHidden })"
        >
          {{ allHidden ? 'Mostrar año' : 'Ocultar año' }}
        </button>
        <button
          v-if="isAdmin"
          type="button"
          class="ds-btn ds-btn--sm ds-btn--danger"
          :disabled="!fiscalYear.can_delete"
          :title="deleteYearTitle"
          @click="emit('delete-year', fiscalYear)"
        >
          Eliminar año
        </button>
      </div>
    </header>

    <div v-if="expanded" class="ds-fy-card__body">
      <div class="ds-fy-grid">
        <button
          v-for="tile in tiles"
          :key="tile.month"
          type="button"
          class="ds-fy-tile"
          :class="{
            'is-missing': !tile.period,
            'is-closed': tile.period?.status === 'CLOSED',
            'is-active': tile.period?.is_active,
            'is-hidden': tile.period?.is_hidden,
            'is-selected': selectedMonth === tile.month && tile.period,
          }"
          :disabled="!tile.period && !isAdmin"
          :title="tileTitle(tile)"
          @click="onTileClick(tile)"
        >
          <span class="ds-fy-tile__month">{{ tile.short }}</span>
          <template v-if="tile.period">
            <span class="ds-fy-tile__status">
              {{ tile.period.status === 'CLOSED' ? '🔒 Cerrado' : 'Abierto' }}
            </span>
            <span class="ds-fy-tile__flags">
              <span v-if="tile.period.is_active" class="ds-fy-tile__flag ds-fy-tile__flag--gold">Activo</span>
              <span v-if="tile.period.is_hidden" class="ds-fy-tile__flag">Oculto</span>
              <span v-if="tile.period.has_data" class="ds-fy-tile__flag ds-fy-tile__flag--data">Con datos</span>
            </span>
          </template>
          <span v-else class="ds-fy-tile__status">{{ isAdmin ? '+ Generar' : 'No generado' }}</span>
        </button>
      </div>

      <div v-if="selectedPeriod" class="ds-fy-detail">
        <div class="ds-fy-detail__info">
          <strong>{{ selectedPeriod.label }}</strong>
          <span class="text-muted">
            {{ formatDateLong(selectedPeriod.start_date) }} – {{ formatDateLong(selectedPeriod.end_date) }}
          </span>
          <Badge :variant="selectedPeriod.status" size="sm">{{ selectedPeriod.status_label }}</Badge>
          <span v-if="selectedPeriod.closed_by_username" class="text-muted">
            Cerrado por {{ selectedPeriod.closed_by_username }}
          </span>
        </div>
        <div class="ds-row-actions">
          <button
            v-if="!selectedPeriod.is_active && isAccountant"
            type="button"
            class="ds-btn ds-btn--sm ds-btn--outline"
            @click="emit('activate', selectedPeriod)"
          >
            Marcar activo
          </button>
          <button
            v-if="isAccountant"
            type="button"
            class="ds-btn ds-btn--sm ds-btn--ghost"
            :disabled="selectedPeriod.is_active && !selectedPeriod.is_hidden"
            :title="selectedPeriod.is_active ? 'El período activo no puede ocultarse' : ''"
            @click="emit('set-hidden', { period: selectedPeriod, hidden: !selectedPeriod.is_hidden })"
          >
            {{ selectedPeriod.is_hidden ? 'Mostrar en selector' : 'Ocultar del selector' }}
          </button>
          <button
            v-if="selectedPeriod.status === 'CLOSED' && isAdmin"
            type="button"
            class="ds-btn ds-btn--sm ds-btn--primary"
            @click="emit('reopen', selectedPeriod)"
          >
            Reabrir período
          </button>
          <button
            v-if="isAdmin"
            type="button"
            class="ds-btn ds-btn--sm ds-btn--danger"
            :disabled="!selectedPeriod.can_delete"
            :title="deletePeriodTitle"
            @click="emit('delete', selectedPeriod)"
          >
            Eliminar período
          </button>
        </div>
      </div>
    </div>
  </article>
</template>
