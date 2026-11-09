<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import http from '@/api/http'
import { usePeriodStore } from '@/stores/period'
import { useAuthStore } from '@/stores/auth'
import { Badge, DataTable, KpiCard, MoneyCell } from '@/components/ui'
import { formatDateShort, formatMoney } from '@/utils/formatters'

const periodStore = usePeriodStore()
const authStore = useAuthStore()

const health = ref({ status: 'checking…' })
const loading = ref(false)
const summary = ref({
  sales: {
    total: '0.00',
    taxable: '0.00',
    iva_debit: '0.00',
    services_total: '0.00',
    products_total: '0.00',
    services_count: 0,
    products_count: 0,
    documents_count: 0,
  },
  purchases: {
    total: '0.00',
    taxable: '0.00',
    iva_credit: '0.00',
    vitrina_total: '0.00',
    cabina_total: '0.00',
    documents_count: 0,
  },
  tax: {
    iva_debit: '0.00',
    iva_credit: '0.00',
    iva_net_payable: '0.00',
    iva_credit_remainder: '0.00',
  },
  cash_balance: '0.00',
  inventory: {
    vitrina_value: '0.00',
    cabina_value: '0.00',
    critical_stock_count: 0,
    critical_stock_items: [],
  },
  journal: {
    posted_count: 0,
    draft_count: 0,
    recent_entries: [],
  },
})

const entryColumns = [
  { key: 'entry_number', label: 'Partida', width: '110px' },
  { key: 'entry_date', label: 'Fecha', type: 'date', width: '100px' },
  { key: 'entry_type', label: 'Origen', width: '120px' },
  { key: 'description', label: 'Concepto' },
  { key: 'status', label: 'Estado', width: '110px' },
  { key: 'total', label: 'Monto', type: 'money', align: 'right', width: '130px' },
]

async function loadDashboard() {
  loading.value = true
  try {
    const [healthResp, dashResp] = await Promise.all([
      http.get('/health/').catch((e) => ({ data: { status: 'error', detail: e.message } })),
      http
        .get('/v1/dashboard/summary/', {
          params: { period: periodStore.activePeriod?.id },
        })
        .catch(() => null),
    ])
    health.value = healthResp.data
    if (dashResp?.data) {
      summary.value = dashResp.data
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => periodStore.activePeriod?.id,
  () => {
    loadDashboard()
  }
)

onMounted(() => {
  loadDashboard()
})
</script>

<template>
  <section class="ds-page">
    <header class="ds-page__header">
      <div>
        <div class="ds-page__eyebrow">RESUMEN EJECUTIVO &amp; FISCAL · NIIF PYMES</div>
        <h1 class="ds-page__title">Panel de Control — {{ periodStore.periodLabel }}</h1>
      </div>
      <div class="ds-page__actions">
        <button type="button" class="ds-btn ds-btn--outline" @click="loadDashboard">
          ↻ Actualizar indicadores
        </button>
        <RouterLink to="/libro-ventas" class="ds-btn ds-btn--primary">
          + Registrar operación
        </RouterLink>
      </div>
    </header>

    <!-- 4 Primary KPI Cards (RF-PAN-01) -->
    <div class="ds-kpi-grid">
      <KpiCard
        title="Ventas brutas del período"
        :value="summary.sales.total"
        tone="wine"
        :badge="`${summary.sales.documents_count} docs`"
        badge-variant="VITRINA"
        :subtitle="`Base gravada: ${formatMoney(summary.sales.taxable)} · Débito IVA: ${formatMoney(summary.sales.iva_debit)}`"
      />

      <KpiCard
        title="Compras registradas (CCF)"
        :value="summary.purchases.total"
        tone="gold"
        :badge="`${summary.purchases.documents_count} docs`"
        badge-variant="CABINA"
        :subtitle="`Base gravada: ${formatMoney(summary.purchases.taxable)} · Crédito IVA: ${formatMoney(summary.purchases.iva_credit)}`"
      />

      <KpiCard
        title="IVA por pagar a Hacienda (13%)"
        :value="summary.tax.iva_net_payable"
        tone="ink"
        :badge="Number(summary.tax.iva_credit_remainder) > 0 ? 'Remanente a favor' : 'Liquidación'"
        :badge-variant="Number(summary.tax.iva_credit_remainder) > 0 ? 'OK' : 'WARNING'"
        :subtitle="`Débito ${formatMoney(summary.tax.iva_debit)} − Crédito ${formatMoney(summary.tax.iva_credit)}`"
      />

      <KpiCard
        title="Efectivo y Bancos (1101)"
        :value="summary.cash_balance"
        tone="default"
        :badge="`${summary.journal.posted_count} partidas`"
        badge-variant="POSTED"
        :subtitle="`Borradores pendientes: ${summary.journal.draft_count}`"
      />
    </div>

    <!-- Dual Regime Cards: Cabina vs Vitrina -->
    <div class="ds-grid-2">
      <div class="ds-panel ds-panel--gold">
        <div class="ds-panel__header">
          <div>
            <Badge variant="CABINA">CABINA · SERVICIOS</Badge>
            <h2 class="ds-panel__title">Ingresos e Insumos de Estación</h2>
          </div>
          <RouterLink to="/inventario" class="ds-btn-link">Ver inventario →</RouterLink>
        </div>
        <div class="ds-stat-row">
          <div>
            <span class="ds-stat-row__label">Ventas de servicios (510101)</span>
            <div class="ds-stat-row__val"><MoneyCell :value="summary.sales.services_total" bold /></div>
            <small>{{ summary.sales.services_count }} atenciones facturadas</small>
          </div>
          <div>
            <span class="ds-stat-row__label">Insumos en estación al costo (110402)</span>
            <div class="ds-stat-row__val"><MoneyCell :value="summary.inventory.cabina_value" bold /></div>
            <small>Compras período: {{ formatMoney(summary.purchases.cabina_total) }}</small>
          </div>
        </div>
      </div>

      <div class="ds-panel ds-panel--wine">
        <div class="ds-panel__header">
          <div>
            <Badge variant="VITRINA">VITRINA · RETAIL</Badge>
            <h2 class="ds-panel__title">Venta Comercial y Mercadería</h2>
          </div>
          <RouterLink to="/libro-ventas" class="ds-btn-link">Ver libro de ventas →</RouterLink>
        </div>
        <div class="ds-stat-row">
          <div>
            <span class="ds-stat-row__label">Venta de productos (510201)</span>
            <div class="ds-stat-row__val"><MoneyCell :value="summary.sales.products_total" bold /></div>
            <small>{{ summary.sales.products_count }} facturas retail</small>
          </div>
          <div>
            <span class="ds-stat-row__label">Inventario vitrina al costo (110401)</span>
            <div class="ds-stat-row__val"><MoneyCell :value="summary.inventory.vitrina_value" bold /></div>
            <small>Compras período: {{ formatMoney(summary.purchases.vitrina_total) }}</small>
          </div>
        </div>
      </div>
    </div>

    <!-- Critical Stock + Recent Journal Entries -->
    <div class="ds-grid-2">
      <div class="ds-panel">
        <div class="ds-panel__header">
          <div>
            <h2 class="ds-panel__title">Alertas de Stock Crítico</h2>
            <p class="ds-panel__subtitle">Productos con existencia igual o menor al mínimo</p>
          </div>
          <Badge :variant="summary.inventory.critical_stock_count > 0 ? 'DANGER' : 'OK'">
            {{ summary.inventory.critical_stock_count }} alertas
          </Badge>
        </div>

        <div v-if="summary.inventory.critical_stock_items.length === 0" class="ds-empty-box">
          Todos los productos de Vitrina y Cabina están sobre el stock mínimo.
        </div>
        <ul v-else class="ds-alert-list">
          <li
            v-for="item in summary.inventory.critical_stock_items"
            :key="item.id"
            class="ds-alert-list__item"
          >
            <div>
              <strong>{{ item.sku }} · {{ item.name }}</strong>
              <div class="ds-alert-list__meta">
                Existencia actual: <b>{{ item.quantity }}</b> (Mínimo: {{ item.min_stock }})
              </div>
            </div>
            <Badge :variant="item.inventory_type" size="sm">{{ item.inventory_type }}</Badge>
          </li>
        </ul>
      </div>

      <div class="ds-panel">
        <div class="ds-panel__header">
          <div>
            <h2 class="ds-panel__title">Estado de Plataforma y Conexión</h2>
            <p class="ds-panel__subtitle">Configuración fiscal y diagnóstico en vivo</p>
          </div>
          <Badge :variant="health.status === 'ok' ? 'OK' : 'WARNING'">
            API: {{ health.status === 'ok' ? 'CONECTADA' : health.status }}
          </Badge>
        </div>

        <dl class="ds-kv-list">
          <div>
            <dt>Razón social</dt>
            <dd>{{ authStore.company?.legal_name || 'Diamond Salón, S.A. de C.V.' }}</dd>
          </div>
          <div>
            <dt>NIT / NRC</dt>
            <dd>{{ authStore.company?.nit || '0614-000000-000-0' }} · NRC {{ authStore.company?.nrc || '000000-0' }}</dd>
          </div>
          <div>
            <dt>Tasa IVA vigente</dt>
            <dd>13.00% (Ley de IVA El Salvador)</dd>
          </div>
          <div>
            <dt>Motor de Base de Datos</dt>
            <dd>{{ health.database || 'PostgreSQL 17 (NIIF PYMES)' }}</dd>
          </div>
        </dl>
      </div>
    </div>

    <!-- Recent Journal Entries Table -->
    <div class="ds-panel">
      <div class="ds-panel__header">
        <div>
          <h2 class="ds-panel__title">Últimas Partidas del Período</h2>
          <p class="ds-panel__subtitle">Asientos automáticos y manuales registrados en {{ periodStore.periodLabel }}</p>
        </div>
        <RouterLink to="/libro-diario" class="ds-btn ds-btn--sm ds-btn--outline">
          Abrir Libro Diario →
        </RouterLink>
      </div>

      <DataTable
        :columns="entryColumns"
        :rows="summary.journal.recent_entries"
        :loading="loading"
        empty-text="Aún no hay partidas registradas en este período contable."
      >
        <template #cell-entry_number="{ row }">
          <strong>{{ row.entry_number ? `Part. N.º ${row.entry_number}` : `Borrador #${row.id}` }}</strong>
        </template>
        <template #cell-entry_type="{ value }">
          <Badge variant="neutral" size="sm">{{ value }}</Badge>
        </template>
        <template #cell-status="{ value }">
          <Badge :variant="value" size="sm">{{ value }}</Badge>
        </template>
        <template #cell-entry_date="{ value }">
          {{ formatDateShort(value) }}
        </template>
      </DataTable>
    </div>
  </section>
</template>
