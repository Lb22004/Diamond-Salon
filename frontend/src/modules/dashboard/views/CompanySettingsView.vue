<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { usePeriodStore } from '@/stores/period'
import { Badge, ConfirmDialog, DataTable, SearchInput } from '@/components/ui'
import FiscalYearCard from '@/modules/dashboard/components/FiscalYearCard.vue'
import GeneratePeriodsModal from '@/modules/dashboard/components/GeneratePeriodsModal.vue'
import { formatDateTime } from '@/utils/formatters'
import { describeMonths } from '@/utils/months'

const authStore = useAuthStore()
const periodStore = usePeriodStore()
const route = useRoute()

const TABS = ['company', 'periods', 'employees', 'audit']
const activeTab = ref(TABS.includes(route.query.tab) ? route.query.tab : 'company') // 'company' | 'periods' | 'employees' | 'audit'
const feedbackMsg = ref('')
const errorMsg = ref('')

watch(
  () => route.query.tab,
  (tab) => {
    if (TABS.includes(tab)) activeTab.value = tab
  }
)

// 1. Company state
const companyForm = ref({
  legal_name: '',
  trade_name: '',
  nit: '',
  nrc: '',
  economic_activity: '',
  address: '',
  iva_rate: '0.1300',
  currency: 'USD',
  allow_negative_stock: false,
})
const savingCompany = ref(false)

// 2. Periods state
const generateModal = ref(false)
const generateYearInitial = ref(new Date().getFullYear())
const generateMonthsInitial = ref([])
const expandedYears = ref(new Set())
const showArchivedYears = ref(false)
const reopenDialog = ref(false)
const periodToReopen = ref(null)
const reopening = ref(false)
const deleteDialog = ref(false)
const deleteTarget = ref(null) // { type: 'period' | 'year', item }
const deleting = ref(false)
const generatingNext = ref(false)

// 3. Employees state
const employees = ref([])
const newEmployee = ref({ full_name: '', position: 'STYLIST' })

// 4. Audit log state
const auditLogs = ref([])
const loadingAudit = ref(false)
const auditSearch = ref('')
const auditActionFilter = ref('')

const auditColumns = [
  { key: 'created_at', label: 'Fecha y Hora', width: '145px' },
  { key: 'username', label: 'Usuario', width: '130px' },
  { key: 'action', label: 'Acción', width: '120px' },
  { key: 'table_name', label: 'Entidad / Tabla', width: '180px' },
  { key: 'record_id', label: 'ID Reg.', width: '85px' },
  { key: 'summary', label: 'Detalle de cambios (JSON)' },
]

async function loadCompany() {
  const { data } = await http.get('/v1/company/')
  companyForm.value = { ...data }
}

async function saveCompany() {
  savingCompany.value = true
  feedbackMsg.value = ''
  errorMsg.value = ''
  try {
    const { data } = await http.put('/v1/company/', companyForm.value)
    companyForm.value = { ...data }
    authStore.company = data
    feedbackMsg.value = 'Parámetros de la empresa actualizados y registrados en auditoría.'
  } catch {
    errorMsg.value = 'No se pudo actualizar la configuración de la empresa.'
  } finally {
    savingCompany.value = false
  }
}

// --- Fiscal years & periods management -------------------------------------------------

function periodsOfYear(fy) {
  return periodStore.allPeriods.filter((p) => p.fiscal_year === fy.id).sort((a, b) => a.month - b.month)
}

/** A year is "archived" when every period is hidden (the active period never counts against it). */
function isArchivedYear(fy) {
  const periods = periodsOfYear(fy)
  return periods.length > 0 && periods.some((p) => p.is_hidden) && periods.every((p) => p.is_hidden || p.is_active)
}

const sortedFiscalYears = computed(() => [...periodStore.fiscalYears].sort((a, b) => b.year - a.year))
const archivedYearsCount = computed(() => sortedFiscalYears.value.filter(isArchivedYear).length)
const visibleFiscalYears = computed(() =>
  showArchivedYears.value ? sortedFiscalYears.value : sortedFiscalYears.value.filter((fy) => !isArchivedYear(fy))
)

function toggleYear(year) {
  const next = new Set(expandedYears.value)
  if (next.has(year)) next.delete(year)
  else next.add(year)
  expandedYears.value = next
}

function resetMessages() {
  feedbackMsg.value = ''
  errorMsg.value = ''
}

function openGenerateModal({ year, months } = {}) {
  const latest = sortedFiscalYears.value[0]?.year
  generateYearInitial.value = year ?? (latest ? latest + 1 : new Date().getFullYear())
  generateMonthsInitial.value = months ?? []
  generateModal.value = true
}

function onGenerated(data) {
  resetMessages()
  const year = data.fiscal_year?.year
  const months = data.created_months || []
  feedbackMsg.value = months.length
    ? `Se generaron ${months.length} período(s) en ${year}: ${describeMonths(months)}.`
    : `No se generaron períodos nuevos en ${year}; los meses seleccionados ya existían.`
  if (year) expandedYears.value = new Set([...expandedYears.value, year])
}

async function handleGenerateNext() {
  resetMessages()
  generatingNext.value = true
  try {
    const period = await periodStore.generateNextPeriod()
    feedbackMsg.value = `Período ${period.label} generado.`
    expandedYears.value = new Set([...expandedYears.value, period.year])
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo generar el siguiente período.'
  } finally {
    generatingNext.value = false
  }
}

async function handleActivatePeriod(row) {
  resetMessages()
  try {
    await periodStore.activateServerPeriod(row.id)
    feedbackMsg.value = `Período activo cambiado a ${row.label}.`
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo activar el período.'
  }
}

async function handleSetHidden({ period, hidden }) {
  resetMessages()
  try {
    await periodStore.setPeriodHidden(period.id, hidden)
    feedbackMsg.value = hidden
      ? `${period.label} ya no aparece en el selector de períodos.`
      : `${period.label} vuelve a aparecer en el selector de períodos.`
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo cambiar la visibilidad del período.'
  }
}

async function handleSetYearHidden({ fiscalYear, hidden }) {
  resetMessages()
  try {
    const { updated } = await periodStore.setYearHidden(fiscalYear.id, hidden)
    feedbackMsg.value = hidden
      ? `Ejercicio ${fiscalYear.year}: ${updated} mes(es) ocultos del selector.`
      : `Ejercicio ${fiscalYear.year}: ${updated} mes(es) visibles nuevamente.`
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo cambiar la visibilidad del ejercicio.'
  }
}

function askDeletePeriod(period) {
  deleteTarget.value = { type: 'period', item: period }
  deleteDialog.value = true
}

function askDeleteYear(fy) {
  deleteTarget.value = { type: 'year', item: fy }
  deleteDialog.value = true
}

const deleteDialogTitle = computed(() =>
  deleteTarget.value?.type === 'year' ? 'Eliminar ejercicio fiscal' : 'Eliminar período contable'
)

const deleteDialogMessage = computed(() => {
  const target = deleteTarget.value
  if (!target) return ''
  if (target.type === 'year') {
    const fy = target.item
    const months = periodsOfYear(fy).map((p) => p.month)
    return `Se eliminará el ejercicio ${fy.year} y sus ${months.length} período(s)${
      months.length ? ` (${describeMonths(months)})` : ''
    }. Ninguno tiene datos registrados. Esta acción quedará registrada en la bitácora de auditoría.`
  }
  const p = target.item
  const extra = p.is_active ? ' Es el período activo: se activará automáticamente el período abierto más cercano.' : ''
  return `Se eliminará el período ${p.label}, que no tiene datos registrados.${extra} Esta acción quedará registrada en la bitácora de auditoría.`
})

async function confirmDelete(reason) {
  const target = deleteTarget.value
  if (!target) return
  deleting.value = true
  resetMessages()
  try {
    if (target.type === 'year') {
      const result = await periodStore.deleteFiscalYear(target.item.id, reason)
      feedbackMsg.value = `Ejercicio ${result.deleted_year} eliminado (${result.deleted_periods} período(s)).`
    } else {
      const result = await periodStore.deletePeriod(target.item.id, reason)
      feedbackMsg.value = result.fiscal_year_deleted
        ? `Período ${target.item.label} eliminado. El ejercicio ${target.item.year} quedó vacío y también se eliminó.`
        : `Período ${target.item.label} eliminado.`
    }
    deleteDialog.value = false
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo completar la eliminación.'
    deleteDialog.value = false
  } finally {
    deleting.value = false
  }
}

function askReopen(row) {
  periodToReopen.value = row
  reopenDialog.value = true
}

async function confirmReopen(reason) {
  if (!periodToReopen.value) return
  reopening.value = true
  errorMsg.value = ''
  try {
    await periodStore.reopenPeriod(periodToReopen.value.id, reason)
    reopenDialog.value = false
    feedbackMsg.value = `Período ${periodToReopen.value.label} reabierto y auditado.`
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo reabrir el período.'
  } finally {
    reopening.value = false
  }
}

async function loadEmployees() {
  const { data } = await http.get('/v1/employees/')
  employees.value = Array.isArray(data) ? data : data.results || []
}

async function createEmployee() {
  if (!newEmployee.value.full_name.trim()) return
  await http.post('/v1/employees/', newEmployee.value)
  newEmployee.value = { full_name: '', position: 'STYLIST' }
  await loadEmployees()
}

async function loadAuditLogs() {
  if (!authStore.canViewAudit) return
  loadingAudit.value = true
  try {
    const params = {}
    if (auditSearch.value) params.search = auditSearch.value
    if (auditActionFilter.value) params.action = auditActionFilter.value
    const { data } = await http.get('/v1/audit-log/', { params })
    auditLogs.value = Array.isArray(data) ? data : data.results || []
  } finally {
    loadingAudit.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    loadCompany(),
    periodStore.loadManagement(),
    loadEmployees(),
    loadAuditLogs(),
  ])
  const activeYear = periodStore.periods.find((p) => p.is_active)?.year
  if (activeYear) expandedYears.value = new Set([activeYear])
})
</script>

<template>
  <section class="ds-page">
    <header class="ds-page__header">
      <div>
        <div class="ds-page__eyebrow">PLATAFORMA, PERÍODOS &amp; BITÁCORA (RF-SEG-03, RF-SEG-05, RF-CIE)</div>
        <h1 class="ds-page__title">Configuración General y Auditoría</h1>
      </div>
    </header>

    <p v-if="feedbackMsg" class="ds-alert ds-alert--success">{{ feedbackMsg }}</p>
    <p v-if="errorMsg" class="ds-alert ds-alert--danger">{{ errorMsg }}</p>

    <div class="ds-tabs">
      <button
        type="button"
        class="ds-tab"
        :class="{ 'is-active': activeTab === 'company' }"
        @click="activeTab = 'company'"
      >
        Empresa y Parámetros IVA
      </button>
      <button
        type="button"
        class="ds-tab"
        :class="{ 'is-active': activeTab === 'periods' }"
        @click="activeTab = 'periods'"
      >
        Períodos Contables
      </button>
      <button
        type="button"
        class="ds-tab"
        :class="{ 'is-active': activeTab === 'employees' }"
        @click="activeTab = 'employees'"
      >
        Personal de Salón (Cabina)
      </button>
      <button
        v-if="authStore.canViewAudit"
        type="button"
        class="ds-tab"
        :class="{ 'is-active': activeTab === 'audit' }"
        @click="activeTab = 'audit'; loadAuditLogs()"
      >
        Bitácora de Auditoría (Inmutable)
      </button>
    </div>

    <!-- TAB 1: Company -->
    <div v-if="activeTab === 'company'" class="ds-panel">
      <h2 class="ds-panel__title">Datos Fiscales del Contribuyente</h2>
      <p class="ds-panel__subtitle">
        Encabezado legal utilizado en los libros de IVA y estados financieros (NIIF para las PYMES).
      </p>

      <form class="ds-form-grid" style="margin-top: 1rem" @submit.prevent="saveCompany">
        <div class="ds-field">
          <label class="ds-field__label">Razón Social *</label>
          <input
            v-model="companyForm.legal_name"
            type="text"
            class="ds-input"
            :disabled="!authStore.isAdmin"
            required
          />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Nombre Comercial *</label>
          <input
            v-model="companyForm.trade_name"
            type="text"
            class="ds-input"
            :disabled="!authStore.isAdmin"
            required
          />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">NIT *</label>
          <input
            v-model="companyForm.nit"
            type="text"
            class="ds-input"
            :disabled="!authStore.isAdmin"
            required
          />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">NRC *</label>
          <input
            v-model="companyForm.nrc"
            type="text"
            class="ds-input"
            :disabled="!authStore.isAdmin"
            required
          />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Giro / Actividad Económica</label>
          <input
            v-model="companyForm.economic_activity"
            type="text"
            class="ds-input"
            :disabled="!authStore.isAdmin"
          />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Tasa IVA (Decimal, ej. 0.1300 = 13%)</label>
          <input
            v-model="companyForm.iva_rate"
            type="text"
            class="ds-input"
            :disabled="!authStore.isAdmin"
            required
          />
        </div>

        <div class="ds-field" style="grid-column: 1 / -1">
          <label class="ds-field__label">Dirección Fiscal</label>
          <input
            v-model="companyForm.address"
            type="text"
            class="ds-input"
            :disabled="!authStore.isAdmin"
          />
        </div>

        <label class="ds-checkbox" style="grid-column: 1 / -1">
          <input
            v-model="companyForm.allow_negative_stock"
            type="checkbox"
            :disabled="!authStore.isAdmin"
          />
          <span>Permitir existencias negativas en inventario (RN-08 / RF-INV-11)</span>
        </label>

        <div v-if="authStore.isAdmin" style="grid-column: 1 / -1">
          <button type="submit" class="ds-btn ds-btn--primary" :disabled="savingCompany">
            {{ savingCompany ? 'Guardando…' : 'Guardar configuración de empresa' }}
          </button>
        </div>
      </form>
    </div>

    <!-- TAB 2: Accounting Periods -->
    <div v-else-if="activeTab === 'periods'" class="ds-panel">
      <div class="ds-panel__header">
        <div>
          <h2 class="ds-panel__title">Ejercicios y Períodos Contables</h2>
          <p class="ds-panel__subtitle">
            Administre la generación flexible de períodos, visibilidad en selectores y cierres mensuales (RN-03).
          </p>
        </div>
        <div v-if="authStore.isAdmin" class="ds-inline-form">
          <button
            type="button"
            class="ds-btn ds-btn--sm ds-btn--outline"
            :disabled="generatingNext"
            @click="handleGenerateNext"
          >
            {{ generatingNext ? 'Generando…' : '+ Siguiente mes' }}
          </button>
          <button
            type="button"
            class="ds-btn ds-btn--sm ds-btn--primary"
            @click="openGenerateModal()"
          >
            + Generar períodos
          </button>
        </div>
      </div>

      <div v-if="archivedYearsCount > 0" class="ds-periods-toolbar">
        <label class="ds-checkbox">
          <input v-model="showArchivedYears" type="checkbox" />
          <span>Mostrar ejercicios archivados / ocultos ({{ archivedYearsCount }})</span>
        </label>
      </div>

      <div v-if="visibleFiscalYears.length" class="ds-fy-list">
        <FiscalYearCard
          v-for="fy in visibleFiscalYears"
          :key="fy.id"
          :fiscal-year="fy"
          :periods="periodsOfYear(fy)"
          :expanded="expandedYears.has(fy.year)"
          :is-admin="authStore.isAdmin"
          :is-accountant="authStore.isAccountant"
          @toggle="toggleYear(fy.year)"
          @activate="handleActivatePeriod"
          @set-hidden="handleSetHidden"
          @reopen="askReopen"
          @delete="askDeletePeriod"
          @add-months="openGenerateModal"
          @set-year-hidden="handleSetYearHidden"
          @delete-year="askDeleteYear"
        />
      </div>
      <p v-else class="text-muted" style="padding: 2rem 0; text-align: center">
        No hay ejercicios fiscales registrados.
      </p>

      <GeneratePeriodsModal
        v-model="generateModal"
        :initial-year="generateYearInitial"
        :initial-months="generateMonthsInitial"
        @generated="onGenerated"
      />

      <ConfirmDialog
        v-model="reopenDialog"
        title="Reabrir período contable cerrado"
        :message="`¿Desea reabrir el período ${periodToReopen?.label}? Esta acción quedará registrada en la bitácora de auditoría (RF-CIE-05).`"
        confirm-label="Reabrir período"
        require-reason
        :loading="reopening"
        @confirm="confirmReopen"
      />

      <ConfirmDialog
        v-model="deleteDialog"
        :title="deleteDialogTitle"
        :message="deleteDialogMessage"
        confirm-label="Eliminar"
        require-reason
        reason-placeholder="Indique el motivo de la eliminación para la bitácora…"
        :loading="deleting"
        @confirm="confirmDelete"
      />
    </div>

    <!-- TAB 3: Salon Employees -->
    <div v-else-if="activeTab === 'employees'" class="ds-panel">
      <div class="ds-panel__header">
        <div>
          <h2 class="ds-panel__title">Estilistas y Personal de Cabina</h2>
          <p class="ds-panel__subtitle">
            Personal vinculado a atenciones de servicios y consumo de insumos de estación.
          </p>
        </div>
        <form v-if="authStore.isAdmin" class="ds-inline-form" @submit.prevent="createEmployee">
          <input
            v-model="newEmployee.full_name"
            type="text"
            class="ds-input ds-input--sm"
            placeholder="Nombre del estilista…"
            required
          />
          <select v-model="newEmployee.position" class="ds-input ds-input--sm">
            <option value="STYLIST">Estilista</option>
            <option value="MANICURIST">Manicurista</option>
            <option value="RECEPTION">Recepción</option>
            <option value="OTHER">Otro</option>
          </select>
          <button type="submit" class="ds-btn ds-btn--sm ds-btn--primary">+ Agregar</button>
        </form>
      </div>

      <ul class="ds-alert-list">
        <li v-for="emp in employees" :key="emp.id" class="ds-alert-list__item">
          <strong>{{ emp.full_name }}</strong>
          <Badge variant="gold" size="sm">{{ emp.position_label }}</Badge>
        </li>
      </ul>
    </div>

    <!-- TAB 4: Audit Log -->
    <div v-else-if="activeTab === 'audit'" class="ds-panel">
      <DataTable :columns="auditColumns" :rows="auditLogs" :loading="loadingAudit">
        <template #toolbar>
          <div class="ds-toolbar">
            <SearchInput
              v-model="auditSearch"
              placeholder="Filtrar por tabla o usuario…"
              @search="loadAuditLogs"
            />
            <select
              v-model="auditActionFilter"
              class="ds-input ds-input--sm"
              style="max-width: 220px"
              @change="loadAuditLogs"
            >
              <option value="">Todas las acciones</option>
              <option value="LOGIN">LOGIN · Inicio de sesión</option>
              <option value="CREATE">CREATE · Creación</option>
              <option value="UPDATE">UPDATE · Actualización</option>
              <option value="POST">POST · Mayorización</option>
              <option value="REVERSE">REVERSE · Reversión</option>
              <option value="VOID">VOID · Anulación</option>
              <option value="CLOSE">CLOSE · Cierre mensual</option>
              <option value="REOPEN">REOPEN · Reapertura</option>
              <option value="EXPORT">EXPORT · Exportación</option>
            </select>
          </div>
        </template>

        <template #cell-created_at="{ value }">
          {{ formatDateTime(value) }}
        </template>

        <template #cell-action="{ row }">
          <Badge
            :variant="
              row.action === 'REOPEN' || row.action === 'VOID' || row.action === 'REVERSE'
                ? 'DANGER'
                : row.action === 'POST' || row.action === 'CREATE'
                  ? 'OK'
                  : 'neutral'
            "
            size="sm"
          >
            {{ row.action }}
          </Badge>
        </template>

        <template #cell-summary="{ row }">
          <code class="ds-code-snippet">
            {{ JSON.stringify(row.after_data || row.before_data || {}).slice(0, 110) }}
          </code>
        </template>
      </DataTable>
    </div>
  </section>
</template>
