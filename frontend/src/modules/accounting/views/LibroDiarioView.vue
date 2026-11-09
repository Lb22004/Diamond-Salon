<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { usePeriodStore } from '@/stores/period'
import {
  Badge,
  ConfirmDialog,
  DateRangePicker,
  ExportButton,
  FormModal,
  KpiCard,
  MoneyCell,
  SearchInput,
} from '@/components/ui'
import { formatDateShort, formatMoney } from '@/utils/formatters'

const authStore = useAuthStore()
const periodStore = usePeriodStore()
const route = useRoute()

const loading = ref(false)
const entries = ref([])
const leafAccounts = ref([])
const summary = ref({
  posted_count: 0,
  draft_count: 0,
  reversed_count: 0,
  total_debit: '0.00',
  total_credit: '0.00',
  is_balanced: true,
})

// Filters (RF-DIA-07)
const searchQuery = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const accountFilter = ref('')

const feedbackMsg = ref('')
const errorMsg = ref('')

// Manual Entry Modal (RF-DIA-02, RF-DIA-03)
const entryModalOpen = ref(false)
const savingEntry = ref(false)
const formError = ref('')
const editingEntryId = ref(null)
const entryForm = ref({
  entry_date: '2026-11-08',
  entry_type: 'MANUAL',
  description: '',
  lines: [
    { account: null, description: '', debit: '0.00', credit: '0.00' },
    { account: null, description: '', debit: '0.00', credit: '0.00' },
  ],
})

// Reverse & Delete Dialogs (RF-DIA-03, RF-DIA-04)
const reverseDialogOpen = ref(false)
const entryToReverse = ref(null)
const reversing = ref(false)

const deleteDialogOpen = ref(false)
const entryToDelete = ref(null)
const deleting = ref(false)

const entryTypes = [
  { value: 'OPENING', label: 'OPENING · Partida de Apertura', variant: 'gold' },
  { value: 'MANUAL', label: 'MANUAL · Partida Manual', variant: 'ink' },
  { value: 'SALE', label: 'SALE · Venta (FCF/CCF)', variant: 'VITRINA' },
  { value: 'PURCHASE', label: 'PURCHASE · Compra (CCF)', variant: 'CABINA' },
  { value: 'PAYMENT', label: 'PAYMENT · Pago a Proveedor', variant: 'info' },
  { value: 'INVENTORY', label: 'INVENTORY · Consumo / Kárdex', variant: 'gold' },
  { value: 'ADJUSTMENT', label: 'ADJUSTMENT · Ajuste de Stock', variant: 'warning' },
  { value: 'CLOSING', label: 'CLOSING · Liquidación / Cierre', variant: 'wine' },
  { value: 'REVERSAL', label: 'REVERSAL · Partida de Reversión', variant: 'danger' },
]

// Live calculation of manual entry totals & difference (RF-DIA-02)
const formTotals = computed(() => {
  let debitCents = 0n
  let creditCents = 0n

  for (const line of entryForm.value.lines) {
    const d = Math.round(Number(line.debit || 0) * 100)
    const c = Math.round(Number(line.credit || 0) * 100)
    if (!Number.isNaN(d) && d > 0) debitCents += BigInt(d)
    if (!Number.isNaN(c) && c > 0) creditCents += BigInt(c)
  }

  const diffCents = debitCents >= creditCents ? debitCents - creditCents : creditCents - debitCents
  const toStr = (cents) => `${cents / 100n}.${String(cents % 100n).padStart(2, '0')}`

  return {
    debit: toStr(debitCents),
    credit: toStr(creditCents),
    diff: toStr(diffCents),
    isBalanced: debitCents === creditCents && debitCents > 0n,
  }
})

function typeBadgeVariant(entryType) {
  const found = entryTypes.find((t) => t.value === entryType)
  return found?.variant || 'neutral'
}

async function fetchLeafAccounts() {
  try {
    const { data } = await http.get('/v1/accounts/', {
      params: { accepts_entries: 1 },
    })
    leafAccounts.value = Array.isArray(data) ? data : data.results || []
  } catch {
    leafAccounts.value = []
  }
}

async function fetchJournalEntries() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = {
      period: periodStore.activePeriod?.id,
    }
    if (searchQuery.value.trim()) params.search = searchQuery.value.trim()
    if (dateFrom.value) params.date_from = dateFrom.value
    if (dateTo.value) params.date_to = dateTo.value
    if (typeFilter.value) params.entry_type = typeFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    if (accountFilter.value) params.account = accountFilter.value

    const [listResp, sumResp] = await Promise.all([
      http.get('/v1/journal-entries/', { params }),
      http.get('/v1/journal-entries/summary/', { params }),
    ])
    entries.value = Array.isArray(listResp.data)
      ? listResp.data
      : listResp.data.results || []
    summary.value = sumResp.data
  } catch {
    errorMsg.value = 'No se pudo cargar el Libro Diario para el período seleccionado.'
  } finally {
    loading.value = false
  }
}

function defaultDateForPeriod() {
  const p = periodStore.activePeriod
  if (!p) return '2026-11-08'
  return p.start_date || '2026-11-01'
}

function openCreateModal() {
  editingEntryId.value = null
  formError.value = ''
  const firstAcc = leafAccounts.value.find((a) => a.code === '420101')?.id || leafAccounts.value[0]?.id || null
  const secondAcc = leafAccounts.value.find((a) => a.code === '110101')?.id || leafAccounts.value[1]?.id || null

  entryForm.value = {
    entry_date: defaultDateForPeriod(),
    entry_type: 'MANUAL',
    description: '',
    lines: [
      { account: firstAcc, description: '', debit: '0.00', credit: '0.00' },
      { account: secondAcc, description: '', debit: '0.00', credit: '0.00' },
    ],
  }
  entryModalOpen.value = true
}

function openEditDraft(entry) {
  editingEntryId.value = entry.id
  formError.value = ''
  entryForm.value = {
    entry_date: entry.entry_date,
    entry_type: entry.entry_type,
    description: entry.description,
    lines: entry.lines.map((l) => ({
      account: l.account,
      description: l.description || '',
      debit: l.debit,
      credit: l.credit,
    })),
  }
  entryModalOpen.value = true
}

function addLine() {
  entryForm.value.lines.push({
    account: leafAccounts.value[0]?.id || null,
    description: '',
    debit: '0.00',
    credit: '0.00',
  })
}

function removeLine(idx) {
  if (entryForm.value.lines.length <= 2) return
  entryForm.value.lines.splice(idx, 1)
}

function onDebitInput(line) {
  if (Number(line.debit) > 0) {
    line.credit = '0.00'
  }
}

function onCreditInput(line) {
  if (Number(line.credit) > 0) {
    line.debit = '0.00'
  }
}

async function submitEntry(postNow = false) {
  savingEntry.value = true
  formError.value = ''
  feedbackMsg.value = ''
  try {
    const payload = {
      entry_date: entryForm.value.entry_date,
      entry_type: entryForm.value.entry_type,
      description: entryForm.value.description,
      post_now: postNow,
      lines: entryForm.value.lines.map((l) => ({
        account: Number(l.account),
        description: l.description,
        debit: String(l.debit || '0.00'),
        credit: String(l.credit || '0.00'),
      })),
    }

    if (editingEntryId.value) {
      await http.put(`/v1/journal-entries/${editingEntryId.value}/`, payload)
      feedbackMsg.value = postNow
        ? 'Borrador actualizado y mayorizado exitosamente.'
        : 'Borrador de partida actualizado.'
    } else {
      const { data } = await http.post('/v1/journal-entries/', payload)
      feedbackMsg.value = postNow
        ? `Partida N.º ${data.entry_number} mayorizada exitosamente.`
        : `Borrador #${data.id} guardado. Puede editarlo o mayorizarlo cuando esté listo.`
    }
    entryModalOpen.value = false
    await fetchJournalEntries()
  } catch (err) {
    const data = err.response?.data
    formError.value =
      data?.detail ||
      (typeof data === 'object' ? Object.values(data).flat().join(' ') : 'No se pudo guardar la partida.')
  } finally {
    savingEntry.value = false
  }
}

async function postDraftDirect(entry) {
  feedbackMsg.value = ''
  errorMsg.value = ''
  try {
    const { data } = await http.post(`/v1/journal-entries/${entry.id}/post/`)
    feedbackMsg.value = `Partida N.º ${data.entry_number} mayorizada en firme.`
    await fetchJournalEntries()
  } catch (err) {
    errorMsg.value =
      err.response?.data?.detail || 'No se pudo mayorizar el borrador seleccionado.'
  }
}

function askDeleteDraft(entry) {
  entryToDelete.value = entry
  deleteDialogOpen.value = true
}

async function confirmDeleteDraft() {
  if (!entryToDelete.value) return
  deleting.value = true
  try {
    await http.delete(`/v1/journal-entries/${entryToDelete.value.id}/`)
    deleteDialogOpen.value = false
    feedbackMsg.value = `Borrador #${entryToDelete.value.id} eliminado.`
    await fetchJournalEntries()
  } catch (err) {
    deleteDialogOpen.value = false
    errorMsg.value = err.response?.data?.detail || 'No se pudo eliminar el borrador.'
  } finally {
    deleting.value = false
  }
}

function askReverseEntry(entry) {
  entryToReverse.value = entry
  reverseDialogOpen.value = true
}

async function confirmReverse(reason) {
  if (!entryToReverse.value) return
  reversing.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.post(
      `/v1/journal-entries/${entryToReverse.value.id}/reverse/`,
      { reason }
    )
    reverseDialogOpen.value = false
    feedbackMsg.value = `Partida N.º ${entryToReverse.value.entry_number} revertida mediante Partida de Reversión N.º ${data.entry_number}.`
    await fetchJournalEntries()
  } catch (err) {
    reverseDialogOpen.value = false
    errorMsg.value = err.response?.data?.detail || 'No se pudo revertir la partida.'
  } finally {
    reversing.value = false
  }
}

watch(
  () => periodStore.activePeriod?.id,
  () => {
    fetchJournalEntries()
  }
)

onMounted(async () => {
  if (route.query.entry) {
    searchQuery.value = String(route.query.entry)
  }
  await Promise.all([fetchLeafAccounts(), fetchJournalEntries()])
})
</script>

<template>
  <section class="ds-page">
    <header class="ds-page__header">
      <div>
        <div class="ds-page__eyebrow">VISTA 5 · REGISTRO CRONOLÓGICO DE PARTIDAS (RF-DIA)</div>
        <h1 class="ds-page__title">Libro Diario — {{ periodStore.periodLabel }}</h1>
      </div>

      <div class="ds-page__actions">
        <ExportButton
          book="journal"
          label="Exportar Libro Diario"
          :params="{ period: periodStore.activePeriod?.id }"
        />
        <button
          v-if="authStore.isAccountant"
          type="button"
          class="ds-btn ds-btn--primary"
          :disabled="!periodStore.isPeriodOpen"
          @click="openCreateModal"
        >
          + Nueva partida manual
        </button>
      </div>
    </header>

    <p v-if="!periodStore.isPeriodOpen" class="ds-alert ds-alert--danger">
      🔒 El período {{ periodStore.periodLabel }} se encuentra CERRADO. No se permiten nuevos asientos ni reversiones (RN-03).
    </p>
    <p v-if="feedbackMsg" class="ds-alert ds-alert--success">{{ feedbackMsg }}</p>
    <p v-if="errorMsg" class="ds-alert ds-alert--danger">{{ errorMsg }}</p>

    <!-- 4 KPI Summary Cards -->
    <div class="ds-kpi-grid">
      <KpiCard
        title="Partidas Mayorizadas"
        :value="summary.posted_count"
        :is-currency="false"
        tone="wine"
        badge="EN FIRME"
        badge-variant="POSTED"
        :subtitle="`Revertidas en el período: ${summary.reversed_count}`"
      />
      <KpiCard
        title="Borradores en Preparación"
        :value="summary.draft_count"
        :is-currency="false"
        tone="gold"
        badge="BORRADOR"
        badge-variant="DRAFT"
        subtitle="Pendientes de revisión y mayorización"
      />
      <KpiCard
        title="Total Cargos del Período (Debe)"
        :value="summary.total_debit"
        tone="ink"
        badge="DEBE"
        badge-variant="gold"
        subtitle="Suma de movimientos deudores mayorizados"
      />
      <KpiCard
        title="Total Abonos del Período (Haber)"
        :value="summary.total_credit"
        tone="default"
        :badge="summary.is_balanced ? 'Sumas iguales' : 'Descuadre'"
        :badge-variant="summary.is_balanced ? 'OK' : 'DANGER'"
        subtitle="Comprobación de partida doble RN-01"
      />
    </div>

    <!-- Filters Bar (RF-DIA-07) -->
    <div class="ds-table-card">
      <div class="ds-table-card__toolbar">
        <div class="ds-toolbar">
          <SearchInput
            v-model="searchQuery"
            placeholder="Buscar por N.º de partida, concepto o código…"
            @search="fetchJournalEntries"
          />

          <DateRangePicker
            v-model:from="dateFrom"
            v-model:to="dateTo"
            @change="fetchJournalEntries"
          />

          <select
            v-model="typeFilter"
            class="ds-input ds-input--sm"
            style="max-width: 190px"
            @change="fetchJournalEntries"
          >
            <option value="">Todos los orígenes</option>
            <option value="OPENING">Apertura</option>
            <option value="MANUAL">Manual</option>
            <option value="SALE">Venta (FCF/CCF)</option>
            <option value="PURCHASE">Compra (CCF)</option>
            <option value="PAYMENT">Pago proveedor</option>
            <option value="INVENTORY">Inventario / Cabina</option>
            <option value="ADJUSTMENT">Ajuste de stock</option>
            <option value="CLOSING">Cierre mensual</option>
            <option value="REVERSAL">Reversión</option>
          </select>

          <select
            v-model="statusFilter"
            class="ds-input ds-input--sm"
            style="max-width: 170px"
            @change="fetchJournalEntries"
          >
            <option value="">Todos los estados</option>
            <option value="POSTED">Mayorizadas (POSTED)</option>
            <option value="DRAFT">Borradores (DRAFT)</option>
            <option value="REVERSED">Revertidas (REVERSED)</option>
          </select>

          <select
            v-model="accountFilter"
            class="ds-input ds-input--sm"
            style="max-width: 230px"
            @change="fetchJournalEntries"
          >
            <option value="">Todas las cuentas analíticas</option>
            <option v-for="acc in leafAccounts" :key="acc.id" :value="acc.code">
              {{ acc.code }} · {{ acc.name }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Chronological Journal Entries List (RF-DIA-01) -->
    <div v-if="loading" class="ds-panel text-center">Cargando partidas del Libro Diario…</div>

    <div v-else-if="entries.length === 0" class="ds-panel text-center text-muted">
      No se encontraron partidas contables con los filtros seleccionados.
    </div>

    <div v-else class="ds-journal-list">
      <article
        v-for="entry in entries"
        :key="entry.id"
        class="ds-journal-card"
        :class="`ds-journal-card--${entry.status.toLowerCase()}`"
      >
        <header class="ds-journal-card__header">
          <div class="ds-journal-card__meta">
            <span class="ds-journal-card__number">
              {{ entry.entry_number ? `Partida N.º ${entry.entry_number}` : `Borrador #${entry.id}` }}
            </span>
            <span class="ds-journal-card__date">{{ formatDateShort(entry.entry_date) }}</span>
            <Badge :variant="typeBadgeVariant(entry.entry_type)" size="sm">
              {{ entry.entry_type_label }}
            </Badge>
            <Badge :variant="entry.status" size="sm">{{ entry.status_label }}</Badge>

            <RouterLink
              v-if="entry.source_link"
              :to="entry.source_link"
              class="ds-btn-link"
              title="Ir al documento origen (RF-DIA-06)"
            >
              Ver documento ({{ entry.source_app }}) →
            </RouterLink>

            <span v-if="entry.reversal_of_number" class="ds-reversal-tag">
              ↺ Reversión de Partida N.º {{ entry.reversal_of_number }}
            </span>
            <span v-if="entry.reversed_by_number" class="ds-reversal-tag">
              ⚠ Anulada por Partida N.º {{ entry.reversed_by_number }}
            </span>
          </div>

          <div v-if="authStore.isAccountant && periodStore.isPeriodOpen" class="ds-row-actions">
            <template v-if="entry.status === 'DRAFT'">
              <button
                type="button"
                class="ds-btn ds-btn--sm ds-btn--outline"
                @click="openEditDraft(entry)"
              >
                Editar borrador
              </button>
              <button
                type="button"
                class="ds-btn ds-btn--sm ds-btn--primary"
                @click="postDraftDirect(entry)"
              >
                ✓ Mayorizar
              </button>
              <button
                type="button"
                class="ds-btn ds-btn--sm ds-btn--ghost"
                @click="askDeleteDraft(entry)"
              >
                Eliminar
              </button>
            </template>

            <button
              v-else-if="entry.status === 'POSTED'"
              type="button"
              class="ds-btn ds-btn--sm ds-btn--outline"
              @click="askReverseEntry(entry)"
            >
              ↺ Revertir partida
            </button>
          </div>
        </header>

        <p class="ds-journal-card__concept">{{ entry.description }}</p>

        <div class="ds-table-scroll">
          <table class="ds-table ds-table--compact">
            <thead>
              <tr>
                <th style="width: 55px">#</th>
                <th style="width: 115px">Código</th>
                <th>Cuenta Contable</th>
                <th>Concepto / Referencia de Línea</th>
                <th style="width: 145px" class="text-right">Debe (Cargos)</th>
                <th style="width: 145px" class="text-right">Haber (Abonos)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in entry.lines" :key="line.id">
                <td class="text-muted">{{ line.line_no }}</td>
                <td>
                  <RouterLink
                    :to="`/libro-mayor?account=${line.account_code}`"
                    class="ds-account-link"
                  >
                    <code>{{ line.account_code }}</code>
                  </RouterLink>
                </td>
                <td>
                  <span :style="{ paddingLeft: Number(line.credit) > 0 ? '1.25rem' : '0' }">
                    {{ line.account_name }}
                  </span>
                </td>
                <td class="text-muted">{{ line.description || entry.description }}</td>
                <td class="text-right">
                  <MoneyCell :value="line.debit" />
                </td>
                <td class="text-right">
                  <MoneyCell :value="line.credit" />
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="ds-table__totals-row">
                <td colspan="4">
                  <strong>Sumas iguales de la partida</strong>
                  <small class="text-muted" style="margin-left: 0.75rem">
                    Registrado por: {{ entry.created_by_username }}
                  </small>
                </td>
                <td class="text-right">
                  <MoneyCell :value="entry.total_debit" bold :muted-if-zero="false" />
                </td>
                <td class="text-right">
                  <MoneyCell :value="entry.total_credit" bold :muted-if-zero="false" />
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </article>

      <!-- Period Grand Totals Footer (RF-DIA-01) -->
      <div class="ds-journal-grand-total">
        <div>
          <strong>TOTALES ACUMULADOS DEL LIBRO DIARIO ({{ periodStore.periodLabel }})</strong>
          <Badge
            :variant="summary.is_balanced ? 'OK' : 'DANGER'"
            size="sm"
            style="margin-left: 0.75rem"
          >
            {{ summary.is_balanced ? 'Sumas iguales comprobadas' : 'Diferencia detectada' }}
          </Badge>
        </div>
        <div class="ds-journal-grand-total__numbers">
          <div>
            <span>TOTAL DEBE:</span>
            <MoneyCell :value="summary.total_debit" bold :muted-if-zero="false" />
          </div>
          <div>
            <span>TOTAL HABER:</span>
            <MoneyCell :value="summary.total_credit" bold :muted-if-zero="false" />
          </div>
        </div>
      </div>
    </div>

    <!-- Manual Journal Entry Modal (RF-DIA-02, RF-DIA-03) -->
    <FormModal
      v-model="entryModalOpen"
      :title="editingEntryId ? `Editar Borrador #${editingEntryId}` : 'Registrar Partida en Libro Diario'"
      subtitle="Ingrese al menos 2 líneas en cuentas analíticas. La partida solo puede mayorizarse cuando Debe = Haber > $0.00 (RN-01)."
      size="lg"
      :loading="savingEntry"
    >
      <div class="ds-form-grid">
        <div class="ds-field">
          <label class="ds-field__label">Fecha de la Partida *</label>
          <input v-model="entryForm.entry_date" type="date" class="ds-input" required />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Tipo de Asiento *</label>
          <select v-model="entryForm.entry_type" class="ds-input">
            <option value="MANUAL">MANUAL · Partida contable manual</option>
            <option value="OPENING">OPENING · Partida de apertura</option>
            <option value="ADJUSTMENT">ADJUSTMENT · Partida de ajuste</option>
          </select>
        </div>

        <div class="ds-field" style="grid-column: 1 / -1">
          <label class="ds-field__label">Concepto General de la Partida *</label>
          <input
            v-model="entryForm.description"
            type="text"
            class="ds-input"
            placeholder="Ej. Provisión de servicios básicos del salón correspondientes a Noviembre 2026"
            required
          />
        </div>
      </div>

      <div class="ds-table-scroll">
        <table class="ds-table ds-table--compact">
          <thead>
            <tr>
              <th style="width: 40px">#</th>
              <th style="width: 280px">Cuenta Analítica (Hoja) *</th>
              <th>Detalle de Línea</th>
              <th style="width: 135px" class="text-right">Debe ($)</th>
              <th style="width: 135px" class="text-right">Haber ($)</th>
              <th style="width: 45px"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(line, idx) in entryForm.lines" :key="idx">
              <td>{{ idx + 1 }}</td>
              <td>
                <select v-model="line.account" class="ds-input ds-input--sm" required>
                  <option :value="null" disabled>Seleccione cuenta…</option>
                  <option v-for="acc in leafAccounts" :key="acc.id" :value="acc.id">
                    {{ acc.code }} · {{ acc.name }}
                  </option>
                </select>
              </td>
              <td>
                <input
                  v-model="line.description"
                  type="text"
                  class="ds-input ds-input--sm"
                  placeholder="Referencia o detalle opcional…"
                />
              </td>
              <td>
                <input
                  v-model="line.debit"
                  type="number"
                  step="0.01"
                  min="0"
                  class="ds-input ds-input--sm text-right"
                  @input="onDebitInput(line)"
                />
              </td>
              <td>
                <input
                  v-model="line.credit"
                  type="number"
                  step="0.01"
                  min="0"
                  class="ds-input ds-input--sm text-right"
                  @input="onCreditInput(line)"
                />
              </td>
              <td class="text-center">
                <button
                  type="button"
                  class="ds-btn ds-btn--sm ds-btn--ghost"
                  :disabled="entryForm.lines.length <= 2"
                  title="Quitar línea"
                  @click="removeLine(idx)"
                >
                  ×
                </button>
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="ds-table__totals-row">
              <td colspan="3">
                <button type="button" class="ds-btn ds-btn--sm ds-btn--outline" @click="addLine">
                  + Agregar línea de movimiento
                </button>
                <Badge
                  :variant="formTotals.isBalanced ? 'OK' : 'WARNING'"
                  size="sm"
                  style="margin-left: 0.75rem"
                >
                  {{
                    formTotals.isBalanced
                      ? 'Partida cuadrada (Debe = Haber)'
                      : `Diferencia: ${formatMoney(formTotals.diff)}`
                  }}
                </Badge>
              </td>
              <td class="text-right">
                <MoneyCell :value="formTotals.debit" bold :muted-if-zero="false" />
              </td>
              <td class="text-right">
                <MoneyCell :value="formTotals.credit" bold :muted-if-zero="false" />
              </td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <p v-if="formError" class="ds-alert ds-alert--danger">{{ formError }}</p>

      <template #footer>
        <button type="button" class="ds-btn ds-btn--ghost" @click="entryModalOpen = false">
          Cancelar
        </button>
        <button
          type="button"
          class="ds-btn ds-btn--outline"
          :disabled="savingEntry"
          @click="submitEntry(false)"
        >
          Guardar Borrador (DRAFT)
        </button>
        <button
          type="button"
          class="ds-btn ds-btn--primary"
          :disabled="savingEntry || !formTotals.isBalanced"
          @click="submitEntry(true)"
        >
          ✓ Mayorizar Partida (POSTED)
        </button>
      </template>
    </FormModal>

    <!-- Reverse Posted Entry Dialog (RF-DIA-04) -->
    <ConfirmDialog
      v-model="reverseDialogOpen"
      title="Revertir partida contable mayorizada"
      :message="`Las partidas mayorizadas son inmutables (RN-02). Al confirmar, se generará una Partida de Reversión con asientos inversos para anular el efecto de la Partida N.º ${entryToReverse?.entry_number}.`"
      confirm-label="Generar partida de reversión"
      require-reason
      reason-placeholder="Indique el motivo contable de la reversión (ej. error de imputación o monto)…"
      :loading="reversing"
      @confirm="confirmReverse"
    />

    <!-- Delete Draft Dialog -->
    <ConfirmDialog
      v-model="deleteDialogOpen"
      title="Eliminar borrador de partida"
      :message="`¿Está seguro de eliminar el Borrador #${entryToDelete?.id}?`"
      confirm-label="Eliminar borrador"
      :loading="deleting"
      @confirm="confirmDeleteDraft"
    />
  </section>
</template>
