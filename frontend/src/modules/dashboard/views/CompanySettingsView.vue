<script setup>
import { onMounted, ref } from 'vue'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { usePeriodStore } from '@/stores/period'
import { Badge, ConfirmDialog, DataTable, SearchInput } from '@/components/ui'
import { formatDateLong, formatDateTime } from '@/utils/formatters'

const authStore = useAuthStore()
const periodStore = usePeriodStore()

const activeTab = ref('company') // 'company' | 'periods' | 'employees' | 'audit'
const feedbackMsg = ref('')
const errorMsg = ref('')

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
const newYearInput = ref(2027)
const reopenDialog = ref(false)
const periodToReopen = ref(null)
const reopening = ref(false)

// 3. Employees state
const employees = ref([])
const newEmployee = ref({ full_name: '', position: 'STYLIST' })

// 4. Audit log state
const auditLogs = ref([])
const loadingAudit = ref(false)
const auditSearch = ref('')
const auditActionFilter = ref('')

const periodColumns = [
  { key: 'code', label: 'Código', width: '90px' },
  { key: 'label', label: 'Período Mensual' },
  { key: 'start_date', label: 'Inicio' },
  { key: 'end_date', label: 'Fin' },
  { key: 'status', label: 'Estado', align: 'center' },
  { key: 'is_active', label: 'Activo en UI', align: 'center' },
  { key: 'actions', label: 'Acciones', align: 'right' },
]

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

async function handleGenerateYear() {
  feedbackMsg.value = ''
  errorMsg.value = ''
  try {
    await periodStore.generateYear(Number(newYearInput.value))
    feedbackMsg.value = `Ejercicio fiscal ${newYearInput.value} generado con sus 12 períodos mensuales.`
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Error al generar el año fiscal.'
  }
}

async function handleActivatePeriod(row) {
  feedbackMsg.value = ''
  errorMsg.value = ''
  try {
    await periodStore.activateServerPeriod(row.id)
    feedbackMsg.value = `Período activo cambiado a ${row.label}.`
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo activar el período.'
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
    periodStore.fetchPeriods(),
    loadEmployees(),
    loadAuditLogs(),
  ])
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
          <h2 class="ds-panel__title">Períodos Mensuales de Contabilidad</h2>
          <p class="ds-panel__subtitle">
            Solo se permiten asientos, ventas y compras en períodos con estado ABIERTO (RN-03).
          </p>
        </div>
        <div v-if="authStore.isAdmin" class="ds-inline-form">
          <input
            v-model="newYearInput"
            type="number"
            min="2020"
            max="2040"
            class="ds-input ds-input--sm"
            style="width: 100px"
          />
          <button type="button" class="ds-btn ds-btn--sm ds-btn--primary" @click="handleGenerateYear">
            + Generar Año Fiscal
          </button>
        </div>
      </div>

      <DataTable :columns="periodColumns" :rows="periodStore.periods" :page-size="12">
        <template #cell-code="{ value }">
          <strong>{{ value }}</strong>
        </template>
        <template #cell-start_date="{ value }">{{ formatDateLong(value) }}</template>
        <template #cell-end_date="{ value }">{{ formatDateLong(value) }}</template>
        <template #cell-status="{ row }">
          <Badge :variant="row.status" size="sm">{{ row.status_label }}</Badge>
        </template>
        <template #cell-is_active="{ value }">
          <Badge v-if="value" variant="gold" size="sm">ACTIVO POR DEFECTO</Badge>
          <span v-else class="text-muted">—</span>
        </template>
        <template #cell-actions="{ row }">
          <div class="ds-row-actions">
            <button
              v-if="!row.is_active && authStore.isAccountant"
              type="button"
              class="ds-btn ds-btn--sm ds-btn--outline"
              @click="handleActivatePeriod(row)"
            >
              Marcar activo
            </button>
            <button
              v-if="row.status === 'CLOSED' && authStore.isAdmin"
              type="button"
              class="ds-btn ds-btn--sm ds-btn--primary"
              @click="askReopen(row)"
            >
              Reabrir período
            </button>
          </div>
        </template>
      </DataTable>

      <ConfirmDialog
        v-model="reopenDialog"
        title="Reabrir período contable cerrado"
        :message="`¿Desea reabrir el período ${periodToReopen?.label}? Esta acción quedará registrada en la bitácora de auditoría (RF-CIE-05).`"
        confirm-label="Reabrir período"
        require-reason
        :loading="reopening"
        @confirm="confirmReopen"
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
