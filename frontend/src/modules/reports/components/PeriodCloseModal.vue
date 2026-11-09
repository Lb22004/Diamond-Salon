<template>
  <FormModal
    :model-value="modelValue"
    :title="`Cierre Contable Mensual · ${periodLabel}`"
    :subtitle="isClosed ? 'Este período ya se encuentra cerrado e inmutable.' : 'Verificación integral, liquidación mensual de IVA y congelamiento de saldos.'"
    size="lg"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div v-if="loading" class="p-lg text-center text-muted">
      Verificando estado contable del período...
    </div>

    <div v-else-if="preview" class="flex-col gap-md">
      <!-- Status banner -->
      <div
        class="card p-md flex-between"
        :style="{
          background: isClosed ? 'var(--bg-subtle)' : preview.can_close ? 'rgba(46, 107, 78, 0.08)' : 'rgba(184, 134, 11, 0.10)',
          borderColor: isClosed ? 'var(--border-soft)' : preview.can_close ? 'rgba(46, 107, 78, 0.3)' : 'rgba(184, 134, 11, 0.35)'
        }"
      >
        <div>
          <div class="eyebrow">ESTADO DEL PERÍODO</div>
          <div style="font-weight: 600; font-size: 15px; margin-top: 2px">
            {{ periodLabel }} ({{ preview.period?.start_date }} al {{ preview.period?.end_date }})
          </div>
        </div>
        <Badge :variant="isClosed ? 'neutral' : preview.can_close ? 'success' : 'warning'">
          {{ isClosed ? 'CERRADO' : preview.can_close ? 'LISTO PARA CIERRE' : 'PENDIENTE DE VALIDACIÓN' }}
        </Badge>
      </div>

      <!-- Pre-close Checklist (RF-CIE-02) -->
      <div>
        <div class="eyebrow mb-xs">LISTA DE VERIFICACIÓN PRE-CIERRE (RF-CIE-02)</div>
        <div class="flex-col gap-xs">
          <div
            v-for="check in preview.checks"
            :key="check.key"
            class="card p-sm flex-between"
            style="padding: 10px 14px"
          >
            <div>
              <div style="font-weight: 600; font-size: 13.5px">
                <span :style="{ color: check.ok ? 'var(--color-success)' : 'var(--color-danger)', marginRight: '6px' }">
                  {{ check.ok ? '✓' : '✕' }}
                </span>
                {{ check.label }}
              </div>
              <div class="text-muted" style="font-size: 12px; margin-left: 18px">
                {{ check.detail }}
              </div>
            </div>
            <Badge :variant="check.ok ? 'success' : 'danger'">
              {{ check.ok ? 'OK' : 'BLOQUEANTE' }}
            </Badge>
          </div>
        </div>
      </div>

      <!-- Monthly IVA Liquidation Preview (RF-CIE-03) -->
      <div v-if="preview.iva_liquidation" class="card p-md" style="background: var(--bg-subtle)">
        <div class="flex-between mb-sm">
          <div>
            <div class="eyebrow">LIQUIDACIÓN MENSUAL DE IVA (RF-CIE-03)</div>
            <div style="font-weight: 600; font-size: 14px">
              Compensación automática 2107 IVA Débito vs. 110601 IVA Crédito
            </div>
          </div>
          <label v-if="!isClosed && preview.iva_liquidation.requires_entry" class="flex-row gap-xs" style="font-size: 12.5px; cursor: pointer">
            <input v-model="postIvaLiquidation" type="checkbox" />
            <span>Generar partida de liquidación</span>
          </label>
        </div>

        <div class="grid-4 mb-sm" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px">
          <div class="card p-sm">
            <div class="text-muted" style="font-size: 11px">2107 IVA Débito</div>
            <div style="font-weight: 700; font-size: 14px">{{ formatMoney(preview.iva_liquidation.iva_debit) }}</div>
          </div>
          <div class="card p-sm">
            <div class="text-muted" style="font-size: 11px">110601 IVA Crédito</div>
            <div style="font-weight: 700; font-size: 14px">{{ formatMoney(preview.iva_liquidation.iva_credit) }}</div>
          </div>
          <div class="card p-sm">
            <div class="text-muted" style="font-size: 11px">2108 IVA por Pagar</div>
            <div style="font-weight: 700; font-size: 14px; color: var(--color-warning)">
              {{ formatMoney(preview.iva_liquidation.iva_payable) }}
            </div>
          </div>
          <div class="card p-sm">
            <div class="text-muted" style="font-size: 11px">Remanente Crédito</div>
            <div style="font-weight: 700; font-size: 14px; color: var(--color-success)">
              {{ formatMoney(preview.iva_liquidation.credit_remainder) }}
            </div>
          </div>
        </div>

        <div v-if="preview.iva_liquidation.proposed_lines?.length" style="margin-top: 8px">
          <div class="text-muted mb-xs" style="font-size: 11.5px; font-weight: 600">
            Partida de cierre propuesta ({{ preview.period?.end_date }}):
          </div>
          <table class="data-table" style="font-size: 12.5px">
            <thead>
              <tr>
                <th>Código</th>
                <th>Cuenta</th>
                <th class="text-right">Debe</th>
                <th class="text-right">Haber</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(line, idx) in preview.iva_liquidation.proposed_lines" :key="idx">
                <td class="mono">{{ line.account_code }}</td>
                <td>{{ line.account_name }}</td>
                <td class="text-right mono">{{ formatMoney(line.debit) }}</td>
                <td class="text-right mono">{{ formatMoney(line.credit) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Admin Reopen section if closed (RF-CIE-05) -->
      <div v-if="isClosed && isAdmin" class="card p-md">
        <div class="eyebrow mb-xs">REAPERTURA EXCEPCIONAL (SOLO ADMINISTRADOR · RF-CIE-05)</div>
        <p class="text-muted mb-sm" style="font-size: 12.5px">
          Para reabrir este período contable debe registrar una justificación de auditoría.
        </p>
        <input
          v-model="reopenReason"
          type="text"
          class="form-input"
          placeholder="Motivo de reapertura (mínimo 5 caracteres)..."
        />
      </div>

      <div v-if="errorMsg" class="alert alert--danger">
        {{ errorMsg }}
      </div>
      <div v-if="successMsg" class="alert alert--success">
        {{ successMsg }}
      </div>
    </div>

    <template #footer>
      <button type="button" class="btn btn--ghost" @click="$emit('update:modelValue', false)">
        Cerrar ventana
      </button>
      <button
        v-if="isClosed && isAdmin"
        type="button"
        class="btn btn--secondary"
        :disabled="submitting || reopenReason.trim().length < 5"
        @click="handleReopen"
      >
        {{ submitting ? 'Reabriendo...' : 'Reabrir Período' }}
      </button>
      <button
        v-if="!isClosed"
        type="button"
        class="btn btn--primary"
        :disabled="submitting || !preview?.can_close || !canWrite"
        @click="handleClosePeriod"
      >
        {{ submitting ? 'Ejecutando cierre...' : 'Confirmar Cierre Mensual' }}
      </button>
    </template>
  </FormModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { usePeriodStore } from '@/stores/period'
import { formatMoney } from '@/utils/formatters'
import { Badge, FormModal } from '@/components/ui'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  periodId: { type: [Number, String], default: null },
})

const emit = defineEmits(['update:modelValue', 'closed', 'reopened'])

const authStore = useAuthStore()
const periodStore = usePeriodStore()

const loading = ref(false)
const submitting = ref(false)
const preview = ref(null)
const postIvaLiquidation = ref(true)
const reopenReason = ref('')
const errorMsg = ref('')
const successMsg = ref('')

const canWrite = computed(() => authStore.canWrite)
const isAdmin = computed(() => authStore.isAdmin)
const targetPeriodId = computed(() => props.periodId || periodStore.activePeriod?.id)
const periodLabel = computed(() => preview.value?.period?.label || periodStore.activePeriodLabel || 'Período Actual')
const isClosed = computed(() => preview.value?.period?.status === 'CLOSED')

async function loadPreview() {
  if (!targetPeriodId.value) return
  loading.value = true
  errorMsg.value = ''
  successMsg.value = ''
  try {
    const { data } = await http.get(`/v1/periods/${targetPeriodId.value}/close/`)
    preview.value = data
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo cargar la verificación de cierre.'
  } finally {
    loading.value = false
  }
}

async function handleClosePeriod() {
  if (!targetPeriodId.value) return
  submitting.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.post(`/v1/periods/${targetPeriodId.value}/close/`, {
      post_iva_liquidation: postIvaLiquidation.value,
    })
    successMsg.value = `Período cerrado exitosamente. ${data.snapshots_count} saldos congelados.`
    await periodStore.fetchPeriods()
    await loadPreview()
    emit('closed', data)
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Error al ejecutar el cierre mensual.'
  } finally {
    submitting.value = false
  }
}

async function handleReopen() {
  if (!targetPeriodId.value || reopenReason.value.trim().length < 5) return
  submitting.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.post(`/v1/periods/${targetPeriodId.value}/reopen/`, {
      reason: reopenReason.value.trim(),
    })
    successMsg.value = 'Período reabierto correctamente.'
    reopenReason.value = ''
    await periodStore.fetchPeriods()
    await loadPreview()
    emit('reopened', data)
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo reabrir el período.'
  } finally {
    submitting.value = false
  }
}

watch(
  () => [props.modelValue, targetPeriodId.value],
  ([open]) => {
    if (open) loadPreview()
  },
  { immediate: true }
)
</script>
