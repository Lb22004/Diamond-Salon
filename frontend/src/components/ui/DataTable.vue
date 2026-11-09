<script setup>
import { computed, ref, watch } from 'vue'
import MoneyCell from './MoneyCell.vue'
import Badge from './Badge.vue'
import { formatDateShort } from '@/utils/formatters'

const props = defineProps({
  columns: {
    type: Array,
    required: true,
    // Each: { key, label, sortable?, align?: 'left'|'right'|'center', type?: 'text'|'money'|'date', width? }
  },
  rows: {
    type: Array,
    default: () => [],
  },
  rowKey: {
    type: String,
    default: 'id',
  },
  loading: {
    type: Boolean,
    default: false,
  },
  emptyText: {
    type: String,
    default: 'No se encontraron registros para los filtros seleccionados.',
  },
  pageSize: {
    type: Number,
    default: 15,
  },
  totals: {
    type: Object,
    default: null, // e.g. { label: 'Totales del período', debit: '1200.00', credit: '1200.00', balanced: true }
  },
})

const sortKey = ref('')
const sortDir = ref('asc') // 'asc' | 'desc'
const currentPage = ref(1)

watch(
  () => props.rows,
  () => {
    currentPage.value = 1
  }
)

function toggleSort(col) {
  if (!col.sortable) return
  if (sortKey.value === col.key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = col.key
    sortDir.value = 'asc'
  }
}

const sortedRows = computed(() => {
  if (!sortKey.value) return props.rows
  const key = sortKey.value
  const factor = sortDir.value === 'asc' ? 1 : -1
  return [...props.rows].sort((a, b) => {
    const va = a?.[key] ?? ''
    const vb = b?.[key] ?? ''
    const numA = Number(va)
    const numB = Number(vb)
    if (!Number.isNaN(numA) && !Number.isNaN(numB) && va !== '' && vb !== '') {
      return (numA - numB) * factor
    }
    return String(va).localeCompare(String(vb), 'es') * factor
  })
})

const totalPages = computed(() =>
  Math.max(1, Math.ceil(sortedRows.value.length / props.pageSize))
)

const paginatedRows = computed(() => {
  const start = (currentPage.value - 1) * props.pageSize
  return sortedRows.value.slice(start, start + props.pageSize)
})
</script>

<template>
  <div class="ds-table-card">
    <div v-if="$slots.toolbar" class="ds-table-card__toolbar">
      <slot name="toolbar" />
    </div>

    <div class="ds-table-scroll">
      <table class="ds-table">
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              :style="col.width ? { width: col.width } : undefined"
              :class="[
                `text-${col.align || (col.type === 'money' ? 'right' : 'left')}`,
                { 'is-sortable': col.sortable },
              ]"
              @click="toggleSort(col)"
            >
              <span>{{ col.label }}</span>
              <span v-if="col.sortable" class="ds-table__sort-indicator">
                <template v-if="sortKey === col.key">{{ sortDir === 'asc' ? '▲' : '▼' }}</template>
                <template v-else>↕</template>
              </span>
            </th>
          </tr>
        </thead>

        <tbody v-if="loading">
          <tr>
            <td :colspan="columns.length" class="ds-table__state">
              Cargando información contable…
            </td>
          </tr>
        </tbody>

        <tbody v-else-if="paginatedRows.length === 0">
          <tr>
            <td :colspan="columns.length" class="ds-table__state">
              {{ emptyText }}
            </td>
          </tr>
        </tbody>

        <tbody v-else>
          <tr v-for="(row, idx) in paginatedRows" :key="row[rowKey] ?? idx">
            <td
              v-for="col in columns"
              :key="col.key"
              :class="`text-${col.align || (col.type === 'money' ? 'right' : 'left')}`"
            >
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                <MoneyCell v-if="col.type === 'money'" :value="row[col.key]" />
                <span v-else-if="col.type === 'date'">{{ formatDateShort(row[col.key]) }}</span>
                <span v-else>{{ row[col.key] ?? '—' }}</span>
              </slot>
            </td>
          </tr>
        </tbody>

        <tfoot v-if="totals">
          <tr class="ds-table__totals-row">
            <td
              v-for="(col, idx) in columns"
              :key="col.key"
              :class="`text-${col.align || (col.type === 'money' ? 'right' : 'left')}`"
            >
              <template v-if="idx === 0">
                <strong>{{ totals.label || 'TOTALES DEL PERÍODO' }}</strong>
                <Badge
                  v-if="totals.balanced !== undefined"
                  :variant="totals.balanced ? 'OK' : 'DANGER'"
                  size="sm"
                  style="margin-left: 0.5rem"
                >
                  {{ totals.balanced ? 'Sumas iguales comprobadas' : 'Descuadre detectado' }}
                </Badge>
              </template>
              <MoneyCell
                v-else-if="totals[col.key] !== undefined && col.type === 'money'"
                :value="totals[col.key]"
                bold
                :muted-if-zero="false"
              />
              <strong v-else-if="totals[col.key] !== undefined">{{ totals[col.key] }}</strong>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>

    <div v-if="sortedRows.length > pageSize" class="ds-table-card__pagination">
      <span class="ds-table-card__count">
        Mostrando {{ (currentPage - 1) * pageSize + 1 }}–{{
          Math.min(currentPage * pageSize, sortedRows.length)
        }}
        de {{ sortedRows.length }} registros
      </span>
      <div class="ds-table-card__pager">
        <button
          type="button"
          class="ds-btn ds-btn--sm ds-btn--outline"
          :disabled="currentPage <= 1"
          @click="currentPage--"
        >
          Anterior
        </button>
        <span class="ds-table-card__page-indicator">
          Página {{ currentPage }} de {{ totalPages }}
        </span>
        <button
          type="button"
          class="ds-btn ds-btn--sm ds-btn--outline"
          :disabled="currentPage >= totalPages"
          @click="currentPage++"
        >
          Siguiente
        </button>
      </div>
    </div>
  </div>
</template>
