<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { usePeriodStore } from '@/stores/period'
import {
  Badge,
  ConfirmDialog,
  ExportButton,
  FormModal,
  MoneyCell,
  SearchInput,
} from '@/components/ui'

const authStore = useAuthStore()
const periodStore = usePeriodStore()
const route = useRoute()
const router = useRouter()

const loading = ref(false)
const accounts = ref([])
const summary = ref({
  total_debit: '0.00',
  total_credit: '0.00',
  is_balanced: true,
  class_counts: {
    ALL: 0,
    ASSET: 0,
    LIABILITY: 0,
    EQUITY: 0,
    COST_EXPENSE: 0,
    INCOME: 0,
  },
})

const searchQuery = ref(String(route.query.q || ''))
const selectedClass = ref('ALL')
const collapsedCodes = ref(new Set())
const feedbackMsg = ref('')
const errorMsg = ref('')

// (i) Account Detail & Dynamic Rules Modal (RF-CAT-08)
const detailModalOpen = ref(false)
const selectedAccount = ref(null)

// Create / Edit Account Modal (RF-CAT-03, RF-CAT-05)
const formModalOpen = ref(false)
const savingAccount = ref(false)
const formError = ref('')
const editingAccount = ref(null)
const accountForm = ref({
  parent: null,
  code: '',
  name: '',
  level: 1,
  account_type: 'ASSET',
  nature: 'DEBIT',
  classification: 'Subcuenta analítica',
  accepts_entries: true,
  inventory_type: '',
  niif_reference: '',
  debit_rule: '',
  credit_rule: '',
})

// Deactivate Confirm Dialog (RF-CAT-06)
const deactivateDialogOpen = ref(false)
const accountToDeactivate = ref(null)
const deactivating = ref(false)

// Account Mapping Modal (RF-CAT-11)
const mappingModalOpen = ref(false)
const mappings = ref([])
const savingMappingKey = ref('')

const classChips = computed(() => [
  { key: 'ALL', label: 'Todos', count: summary.value.class_counts?.ALL ?? accounts.value.length },
  { key: 'ASSET', label: '1 · Activos', count: summary.value.class_counts?.ASSET ?? 0 },
  { key: 'LIABILITY', label: '2 · Pasivos', count: summary.value.class_counts?.LIABILITY ?? 0 },
  { key: 'EQUITY', label: '3 · Patrimonio', count: summary.value.class_counts?.EQUITY ?? 0 },
  { key: 'COST_EXPENSE', label: '4 · Costos / Gastos', count: summary.value.class_counts?.COST_EXPENSE ?? 0 },
  { key: 'INCOME', label: '5 · Ingresos', count: summary.value.class_counts?.INCOME ?? 0 },
])

const parentCandidates = computed(() =>
  accounts.value.filter(
    (a) =>
      a.level < 4 &&
      (!editingAccount.value || a.id !== editingAccount.value.id)
  )
)

const leafAccounts = computed(() =>
  accounts.value.filter((a) => a.accepts_entries && a.is_active)
)

const visibleAccounts = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return accounts.value.filter((acc) => {
    // Filter by class chip
    if (selectedClass.value === 'COST_EXPENSE') {
      if (!['COST', 'EXPENSE'].includes(acc.account_type)) return false
    } else if (selectedClass.value !== 'ALL' && acc.account_type !== selectedClass.value) {
      return false
    }

    // Search filter (if searching, show matching rows regardless of collapse state)
    if (q) {
      return (
        acc.code.toLowerCase().includes(q) ||
        acc.name.toLowerCase().includes(q) ||
        (acc.classification || '').toLowerCase().includes(q) ||
        (acc.niif_reference || '').toLowerCase().includes(q)
      )
    }

    // Check if any ancestor code is collapsed
    for (const collapsedCode of collapsedCodes.value) {
      if (acc.code !== collapsedCode && acc.code.startsWith(collapsedCode)) {
        return false
      }
    }
    return true
  })
})

function hasChildren(acc) {
  return accounts.value.some((other) => other.parent === acc.id)
}

function toggleCollapse(code) {
  const next = new Set(collapsedCodes.value)
  if (next.has(code)) {
    next.delete(code)
  } else {
    next.add(code)
  }
  collapsedCodes.value = next
}

async function fetchAccounts() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get('/v1/accounts/', {
      params: {
        tree: 1,
        period: periodStore.activePeriod?.id,
      },
    })
    accounts.value = data.results || []
    if (data.summary) {
      summary.value = data.summary
    }
  } catch {
    errorMsg.value = 'No se pudo cargar el catálogo de cuentas.'
  } finally {
    loading.value = false
  }
}

function openDetail(acc) {
  selectedAccount.value = acc
  detailModalOpen.value = true
}

function goToLedger(acc) {
  detailModalOpen.value = false
  router.push({ path: '/libro-mayor', query: { account: acc.code } })
}

function onParentChange() {
  const parent = accounts.value.find((a) => a.id === accountForm.value.parent)
  if (!parent) {
    accountForm.value.level = 1
    accountForm.value.classification = 'Clase'
    accountForm.value.accepts_entries = false
    return
  }
  const nextLevel = parent.level + 1
  accountForm.value.level = nextLevel
  accountForm.value.account_type = parent.account_type
  accountForm.value.nature = parent.nature
  accountForm.value.accepts_entries = nextLevel >= 3
  accountForm.value.classification =
    nextLevel === 2
      ? 'Grupo'
      : nextLevel === 3
        ? 'Cuenta mayor'
        : 'Subcuenta analítica'

  // Suggest next sequential child code under parent
  if (!editingAccount.value) {
    const siblings = accounts.value.filter((a) => a.parent === parent.id)
    const padLen = nextLevel === 2 ? 1 : 2
    const nextIdx = siblings.length + 1
    accountForm.value.code = `${parent.code}${String(nextIdx).padStart(padLen, '0')}`
  }
}

function openCreateModal() {
  editingAccount.value = null
  formError.value = ''
  const defaultParent = accounts.value.find((a) => a.code === '1101') || null
  accountForm.value = {
    parent: defaultParent ? defaultParent.id : null,
    code: defaultParent ? '110103' : '',
    name: '',
    level: defaultParent ? defaultParent.level + 1 : 1,
    account_type: defaultParent ? defaultParent.account_type : 'ASSET',
    nature: defaultParent ? defaultParent.nature : 'DEBIT',
    classification: 'Subcuenta analítica',
    accepts_entries: true,
    inventory_type: '',
    niif_reference: 'NIIF PYMES',
    debit_rule: '',
    credit_rule: '',
  }
  if (defaultParent) onParentChange()
  formModalOpen.value = true
}

function openEditModal(acc) {
  editingAccount.value = acc
  formError.value = ''
  accountForm.value = {
    parent: acc.parent,
    code: acc.code,
    name: acc.name,
    level: acc.level,
    account_type: acc.account_type,
    nature: acc.nature,
    classification: acc.classification || '',
    accepts_entries: acc.accepts_entries,
    inventory_type: acc.inventory_type || '',
    niif_reference: acc.niif_reference || '',
    debit_rule: acc.debit_rule || '',
    credit_rule: acc.credit_rule || '',
  }
  formModalOpen.value = true
}

async function saveAccount() {
  savingAccount.value = true
  formError.value = ''
  feedbackMsg.value = ''
  try {
    const payload = {
      ...accountForm.value,
      inventory_type: accountForm.value.inventory_type || null,
    }
    if (editingAccount.value) {
      await http.patch(`/v1/accounts/${editingAccount.value.id}/`, payload)
      feedbackMsg.value = `Cuenta ${payload.code} (${payload.name}) actualizada.`
    } else {
      await http.post('/v1/accounts/', payload)
      feedbackMsg.value = `Cuenta ${payload.code} (${payload.name}) creada exitosamente.`
    }
    formModalOpen.value = false
    await fetchAccounts()
  } catch (err) {
    const data = err.response?.data
    formError.value =
      data?.detail ||
      (typeof data === 'object' ? Object.values(data).flat().join(' ') : 'Error al guardar la cuenta.')
  } finally {
    savingAccount.value = false
  }
}

function askDeactivate(acc) {
  accountToDeactivate.value = acc
  deactivateDialogOpen.value = true
}

async function confirmDeactivate() {
  if (!accountToDeactivate.value) return
  deactivating.value = true
  errorMsg.value = ''
  feedbackMsg.value = ''
  try {
    await http.delete(`/v1/accounts/${accountToDeactivate.value.id}/`)
    deactivateDialogOpen.value = false
    feedbackMsg.value = `Cuenta ${accountToDeactivate.value.code} desactivada.`
    await fetchAccounts()
  } catch (err) {
    deactivateDialogOpen.value = false
    errorMsg.value =
      err.response?.data?.detail || 'No se pudo desactivar la cuenta seleccionada.'
  } finally {
    deactivating.value = false
  }
}

async function openMappingsModal() {
  mappingModalOpen.value = true
  const { data } = await http.get('/v1/account-mappings/')
  mappings.value = Array.isArray(data) ? data : data.results || []
}

async function updateMapping(row, newAccountId) {
  savingMappingKey.value = row.key
  try {
    const { data } = await http.patch(`/v1/account-mappings/${row.key}/`, {
      account: Number(newAccountId),
    })
    const idx = mappings.value.findIndex((m) => m.key === row.key)
    if (idx !== -1) mappings.value[idx] = data
    feedbackMsg.value = `Mapeo contable «${row.key}» actualizado a ${data.account_code}.`
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo actualizar el mapeo.'
  } finally {
    savingMappingKey.value = ''
  }
}

watch(
  () => periodStore.activePeriod?.id,
  () => {
    fetchAccounts()
  }
)

onMounted(() => {
  fetchAccounts()
})
</script>

<template>
  <section class="ds-page">
    <header class="ds-page__header">
      <div>
        <div class="ds-page__eyebrow">VISTA 1 · ESTRUCTURA CONTABLE NIIF PARA LAS PYMES (RF-CAT)</div>
        <h1 class="ds-page__title">Catálogo de Cuentas y Reglas de Partida Doble</h1>
      </div>

      <div class="ds-page__actions">
        <Badge :variant="summary.is_balanced ? 'OK' : 'DANGER'">
          Estado del plan: {{ summary.is_balanced ? 'BALANCEADO' : 'DESCUADRADO' }}
        </Badge>
        <button
          v-if="authStore.isAccountant"
          type="button"
          class="ds-btn ds-btn--outline"
          @click="openMappingsModal"
        >
          ⚙ Mapeo de Partidas
        </button>
        <ExportButton book="chart" label="Exportar NIIF" :params="{ period: periodStore.activePeriod?.id }" />
        <button
          v-if="authStore.isAccountant"
          type="button"
          class="ds-btn ds-btn--primary"
          @click="openCreateModal"
        >
          + Nueva cuenta
        </button>
      </div>
    </header>

    <p v-if="feedbackMsg" class="ds-alert ds-alert--success">{{ feedbackMsg }}</p>
    <p v-if="errorMsg" class="ds-alert ds-alert--danger">{{ errorMsg }}</p>

    <!-- Search & Filter Chips (RF-CAT-07) -->
    <div class="ds-table-card">
      <div class="ds-table-card__toolbar">
        <div class="ds-toolbar">
          <SearchInput
            v-model="searchQuery"
            placeholder="Buscar por código o nombre: inventario, caja, IVA, vitrina, cabina…"
          />

          <div class="ds-chip-group">
            <button
              v-for="chip in classChips"
              :key="chip.key"
              type="button"
              class="ds-filter-chip"
              :class="{ 'is-active': selectedClass === chip.key }"
              @click="selectedClass = chip.key"
            >
              <span>{{ chip.label }}</span>
              <span class="ds-filter-chip__count">{{ chip.count }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Hierarchical Tree Table (RF-CAT-01, RF-CAT-09) -->
      <div class="ds-table-scroll">
        <table class="ds-table">
          <thead>
            <tr>
              <th style="width: 160px">Código</th>
              <th>Nombre de la Cuenta y Referencia NIIF</th>
              <th style="width: 190px">Clasificación / Nivel</th>
              <th style="width: 130px" class="text-center">Naturaleza</th>
              <th style="width: 145px" class="text-right">Saldo Período</th>
              <th style="width: 185px" class="text-right">Acciones</th>
            </tr>
          </thead>

          <tbody v-if="loading">
            <tr>
              <td colspan="6" class="ds-table__state">Cargando catálogo jerárquico de cuentas…</td>
            </tr>
          </tbody>

          <tbody v-else-if="visibleAccounts.length === 0">
            <tr>
              <td colspan="6" class="ds-table__state">
                No se encontraron cuentas para «{{ searchQuery }}».
              </td>
            </tr>
          </tbody>

          <tbody v-else>
            <tr
              v-for="acc in visibleAccounts"
              :key="acc.id"
              :class="`ds-account-row ds-account-row--lvl-${acc.level}`"
            >
              <td>
                <div
                  class="ds-account-code"
                  :style="{ paddingLeft: `${(acc.level - 1) * 1.15}rem` }"
                >
                  <button
                    v-if="hasChildren(acc)"
                    type="button"
                    class="ds-tree-toggle"
                    :title="collapsedCodes.has(acc.code) ? 'Expandir' : 'Contraer'"
                    @click="toggleCollapse(acc.code)"
                  >
                    {{ collapsedCodes.has(acc.code) ? '▸' : '▾' }}
                  </button>
                  <span v-else class="ds-tree-leaf-dot">•</span>
                  <code>{{ acc.code }}</code>
                </div>
              </td>

              <td>
                <div class="ds-account-name-cell">
                  <span :class="{ 'font-bold': acc.level <= 3 }">{{ acc.name }}</span>
                  <Badge
                    v-if="acc.inventory_type"
                    :variant="acc.inventory_type"
                    size="sm"
                  >
                    {{ acc.inventory_type }}
                  </Badge>
                  <span v-if="acc.niif_reference" class="ds-niif-tag">{{ acc.niif_reference }}</span>
                </div>
              </td>

              <td>
                <div class="ds-account-meta">
                  <span>{{ acc.classification || acc.level_label }}</span>
                  <small class="text-muted">
                    {{ acc.level_label }} · {{ acc.accepts_entries ? 'Analítica (Mayorizable)' : 'Agrupación' }}
                  </small>
                </div>
              </td>

              <td class="text-center">
                <Badge :variant="acc.nature === 'DEBIT' ? 'gold' : 'wine'" size="sm">
                  {{ acc.nature_label }}
                </Badge>
              </td>

              <td class="text-right">
                <MoneyCell :value="acc.balance" :bold="acc.level <= 2" />
              </td>

              <td class="text-right">
                <div class="ds-row-actions" style="justify-content: flex-end">
                  <button
                    type="button"
                    class="ds-btn ds-btn--sm ds-btn--outline"
                    title="Ver reglas de cargo/abono y saldo (RF-CAT-08)"
                    @click="openDetail(acc)"
                  >
                    ⓘ Reglas
                  </button>
                  <button
                    v-if="authStore.isAccountant"
                    type="button"
                    class="ds-btn ds-btn--sm ds-btn--outline"
                    @click="openEditModal(acc)"
                  >
                    Editar
                  </button>
                  <button
                    v-if="authStore.isAccountant && acc.level >= 3 && !acc.has_movements"
                    type="button"
                    class="ds-btn ds-btn--sm ds-btn--ghost"
                    title="Desactivar cuenta sin saldo (RF-CAT-06)"
                    @click="askDeactivate(acc)"
                  >
                    ×
                  </button>
                </div>
              </td>
            </tr>
          </tbody>

          <tfoot>
            <tr class="ds-table__totals-row">
              <td colspan="4">
                <strong>SUMAS COMPROBADAS DE CUENTAS ANALÍTICAS ({{ periodStore.periodLabel }})</strong>
                <Badge
                  :variant="summary.is_balanced ? 'OK' : 'DANGER'"
                  size="sm"
                  style="margin-left: 0.6rem"
                >
                  {{ summary.is_balanced ? 'Σ Debe = Σ Haber' : 'Diferencia detectada' }}
                </Badge>
              </td>
              <td class="text-right">
                <span class="text-muted" style="font-size: 0.75rem; display: block">Debe / Haber acumulados</span>
                <MoneyCell :value="summary.total_debit" bold :muted-if-zero="false" />
              </td>
              <td class="text-right">
                <span class="text-muted" style="font-size: 0.75rem; display: block">Total Abonos</span>
                <MoneyCell :value="summary.total_credit" bold :muted-if-zero="false" />
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>

    <!-- (i) Dynamic Debit / Credit Rules & Balance Modal (RF-CAT-08) -->
    <FormModal
      v-model="detailModalOpen"
      :title="selectedAccount ? `${selectedAccount.code} · ${selectedAccount.name}` : 'Detalle de cuenta'"
      :subtitle="
        selectedAccount
          ? `${selectedAccount.level_label} · Naturaleza ${selectedAccount.nature_label} · ${selectedAccount.niif_reference || 'NIIF PYMES'}`
          : ''
      "
      size="md"
      hide-footer
    >
      <template v-if="selectedAccount">
        <div class="ds-kpi-grid">
          <div class="ds-panel">
            <span class="ds-stat-row__label">Total Cargos (Debe)</span>
            <div class="ds-stat-row__val"><MoneyCell :value="selectedAccount.debit_total" bold /></div>
          </div>
          <div class="ds-panel">
            <span class="ds-stat-row__label">Total Abonos (Haber)</span>
            <div class="ds-stat-row__val"><MoneyCell :value="selectedAccount.credit_total" bold /></div>
          </div>
          <div class="ds-panel ds-panel--gold">
            <span class="ds-stat-row__label">Saldo Actual ({{ selectedAccount.nature_label }})</span>
            <div class="ds-stat-row__val"><MoneyCell :value="selectedAccount.balance" bold /></div>
          </div>
        </div>

        <div class="ds-rules-grid">
          <div class="ds-rule-box ds-rule-box--debit">
            <h4>➕ ¿Cuándo se CARGA (Debe)?</h4>
            <p>
              {{
                selectedAccount.debit_rule ||
                'Se carga por los aumentos o cargos según su naturaleza contable bajo NIIF para las PYMES.'
              }}
            </p>
          </div>
          <div class="ds-rule-box ds-rule-box--credit">
            <h4>➖ ¿Cuándo se ABONA (Haber)?</h4>
            <p>
              {{
                selectedAccount.credit_rule ||
                'Se abona por las disminuciones o abonos registrados en el Libro Diario.'
              }}
            </p>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 0.5rem">
          <Badge :variant="selectedAccount.accepts_entries ? 'OK' : 'neutral'">
            {{ selectedAccount.accepts_entries ? 'Cuenta analítica (Recibe partidas)' : 'Cuenta agrupadora (Suma subcuentas)' }}
          </Badge>
          <button type="button" class="ds-btn ds-btn--primary" @click="goToLedger(selectedAccount)">
            Consultar en Libro Mayor →
          </button>
        </div>
      </template>
    </FormModal>

    <!-- Create / Edit Account Modal (RF-CAT-03, RF-CAT-05) -->
    <FormModal
      v-model="formModalOpen"
      :title="editingAccount ? `Editar cuenta ${editingAccount.code}` : 'Nueva cuenta contable NIIF'"
      subtitle="Codificación decimal acumulativa (1 Clase, 2 Grupo, 4 Mayor, 6 Subcuenta · RF-CAT-02)"
      size="lg"
      :loading="savingAccount"
      @submit="saveAccount"
    >
      <p v-if="editingAccount?.has_movements" class="ds-alert ds-alert--success">
        🔒 Esta cuenta ya registra movimientos contables. Su código, naturaleza y cuenta padre están protegidos (RF-CAT-05).
      </p>

      <div class="ds-form-grid">
        <div class="ds-field">
          <label class="ds-field__label">Cuenta Padre (Jerarquía)</label>
          <select
            v-model="accountForm.parent"
            class="ds-input"
            :disabled="Boolean(editingAccount?.has_movements)"
            @change="onParentChange"
          >
            <option :value="null">— Sin padre (Nivel 1 · Clase) —</option>
            <option v-for="p in parentCandidates" :key="p.id" :value="p.id">
              {{ p.code }} · {{ p.name }} ({{ p.level_label }})
            </option>
          </select>
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Código Contable *</label>
          <input
            v-model="accountForm.code"
            type="text"
            class="ds-input"
            placeholder="Ej. 110103"
            :disabled="Boolean(editingAccount?.has_movements)"
            required
          />
        </div>

        <div class="ds-field" style="grid-column: 1 / -1">
          <label class="ds-field__label">Nombre de la Cuenta *</label>
          <input
            v-model="accountForm.name"
            type="text"
            class="ds-input"
            placeholder="Ej. Caja chica recepción"
            required
          />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Tipo de Cuenta *</label>
          <select
            v-model="accountForm.account_type"
            class="ds-input"
            :disabled="Boolean(editingAccount?.has_movements)"
          >
            <option value="ASSET">1 · Activo (ASSET)</option>
            <option value="LIABILITY">2 · Pasivo (LIABILITY)</option>
            <option value="EQUITY">3 · Patrimonio (EQUITY)</option>
            <option value="COST">41 · Costo (COST)</option>
            <option value="EXPENSE">42 · Gasto (EXPENSE)</option>
            <option value="INCOME">5 · Ingreso (INCOME)</option>
          </select>
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Naturaleza del Saldo *</label>
          <select
            v-model="accountForm.nature"
            class="ds-input"
            :disabled="Boolean(editingAccount?.has_movements)"
          >
            <option value="DEBIT">Deudora (Debe − Haber)</option>
            <option value="CREDIT">Acreedora (Haber − Debe)</option>
          </select>
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Etiqueta de Clasificación</label>
          <input
            v-model="accountForm.classification"
            type="text"
            class="ds-input"
            placeholder="Ej. Subcuenta analítica, Obligación fiscal…"
          />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Régimen Mixto (Vitrina / Cabina)</label>
          <select v-model="accountForm.inventory_type" class="ds-input">
            <option value="">— No aplica (General) —</option>
            <option value="VITRINA">VITRINA (Mercadería / Venta retail)</option>
            <option value="CABINA">CABINA (Insumos / Servicios)</option>
          </select>
        </div>

        <div class="ds-field" style="grid-column: 1 / -1">
          <label class="ds-field__label">Referencia NIIF PYMES / Base Legal</label>
          <input
            v-model="accountForm.niif_reference"
            type="text"
            class="ds-input"
            placeholder="Ej. NIIF PYMES Secc. 13.18 / Ley de IVA Art. 65"
          />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Regla de Cargo (Se carga cuando…)</label>
          <textarea
            v-model="accountForm.debit_rule"
            rows="3"
            class="ds-input"
            placeholder="Describa en qué operaciones se carga esta cuenta…"
          />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Regla de Abono (Se abona cuando…)</label>
          <textarea
            v-model="accountForm.credit_rule"
            rows="3"
            class="ds-input"
            placeholder="Describa en qué operaciones se abona esta cuenta…"
          />
        </div>
      </div>

      <label class="ds-checkbox">
        <input
          v-model="accountForm.accepts_entries"
          type="checkbox"
          :disabled="Boolean(editingAccount?.has_movements)"
        />
        <span>Cuenta hoja / analítica (acepta líneas directas en el Libro Diario · RF-CAT-04)</span>
      </label>

      <p v-if="formError" class="ds-alert ds-alert--danger">{{ formError }}</p>
    </FormModal>

    <!-- Configurable Account Mapping Modal (RF-CAT-11) -->
    <FormModal
      v-model="mappingModalOpen"
      title="Mapeo de Eventos del Motor de Partidas (PostingService)"
      subtitle="Asocia cada evento operativo con su cuenta analítica NIIF sin códigos fijos en código fuente (RN-12)"
      size="lg"
      hide-footer
    >
      <div class="ds-table-scroll">
        <table class="ds-table">
          <thead>
            <tr>
              <th>Clave de Evento</th>
              <th>Descripción Operativa</th>
              <th>Cuenta Analítica Vinculada</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in mappings" :key="m.key">
              <td><code>{{ m.key }}</code></td>
              <td>{{ m.description }}</td>
              <td>
                <select
                  class="ds-input ds-input--sm"
                  :value="m.account"
                  :disabled="savingMappingKey === m.key"
                  @change="updateMapping(m, $event.target.value)"
                >
                  <option v-for="leaf in leafAccounts" :key="leaf.id" :value="leaf.id">
                    {{ leaf.code }} · {{ leaf.name }}
                  </option>
                </select>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </FormModal>

    <!-- Deactivate Account Confirm Dialog (RF-CAT-06) -->
    <ConfirmDialog
      v-model="deactivateDialogOpen"
      title="Desactivar cuenta contable"
      :message="`¿Desea desactivar la cuenta ${accountToDeactivate?.code} (${accountToDeactivate?.name})? Las cuentas nunca se eliminan físicamente (RF-CAT-06).`"
      confirm-label="Desactivar cuenta"
      :loading="deactivating"
      @confirm="confirmDeactivate"
    />
  </section>
</template>
