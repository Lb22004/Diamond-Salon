<script setup>
import { computed, ref, watch } from 'vue'
import { usePeriodStore } from '@/stores/period'
import FormModal from '@/components/ui/FormModal.vue'
import MonthGrid from '@/components/ui/MonthGrid.vue'
import { MONTH_NAMES_ES, describeMonths } from '@/utils/months'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  /** Year pre-filled when the modal opens. */
  initialYear: {
    type: Number,
    default: () => new Date().getFullYear(),
  },
  /** Months pre-selected in MONTHS mode (e.g. clicking a missing month tile). */
  initialMonths: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:modelValue', 'generated'])
const periodStore = usePeriodStore()

const year = ref(props.initialYear)
const mode = ref('FULL') // 'FULL' | 'RANGE' | 'MONTHS'
const startMonth = ref(1)
const endMonth = ref(12)
const selectedMonths = ref([])
const saving = ref(false)
const error = ref('')

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    year.value = props.initialYear
    error.value = ''
    if (props.initialMonths.length) {
      mode.value = 'MONTHS'
      selectedMonths.value = [...props.initialMonths]
    } else {
      mode.value = 'FULL'
      selectedMonths.value = []
    }
    const existing = existingMonths.value
    const firstMissing = [...Array(12).keys()].map((i) => i + 1).find((m) => !existing.includes(m))
    startMonth.value = firstMissing || 1
    endMonth.value = 12
  }
)

const existingPeriods = computed(() =>
  periodStore.allPeriods.filter((p) => p.year === Number(year.value))
)
const existingMonths = computed(() => existingPeriods.value.map((p) => p.month))

const requestedMonths = computed(() => {
  if (mode.value === 'FULL') return [...Array(12).keys()].map((i) => i + 1)
  if (mode.value === 'RANGE') {
    const a = Number(startMonth.value)
    const b = Number(endMonth.value)
    if (a > b) return []
    return [...Array(b - a + 1).keys()].map((i) => a + i)
  }
  return selectedMonths.value
})

const newMonths = computed(() => requestedMonths.value.filter((m) => !existingMonths.value.includes(m)))

const yearValid = computed(() => Number.isInteger(Number(year.value)) && year.value >= 2000 && year.value <= 2100)

const previewText = computed(() => {
  if (!yearValid.value) return 'Indique un año entre 2000 y 2100.'
  if (mode.value === 'RANGE' && Number(startMonth.value) > Number(endMonth.value)) {
    return 'El mes inicial no puede ser posterior al mes final.'
  }
  if (newMonths.value.length === 0) return 'No hay meses nuevos por generar con esta selección.'
  return `Se crearán ${newMonths.value.length} período(s) en ${year.value}: ${describeMonths(newMonths.value)}.`
})

const canSubmit = computed(() => yearValid.value && newMonths.value.length > 0 && !saving.value)

async function submit() {
  if (!canSubmit.value) return
  saving.value = true
  error.value = ''
  try {
    const payload = { year: Number(year.value), mode: mode.value }
    if (mode.value === 'RANGE') {
      payload.start_month = Number(startMonth.value)
      payload.end_month = Number(endMonth.value)
    } else if (mode.value === 'MONTHS') {
      payload.months = selectedMonths.value
    }
    const data = await periodStore.generatePeriods(payload)
    emit('generated', data)
    emit('update:modelValue', false)
  } catch (err) {
    error.value = err.response?.data?.detail || 'No se pudieron generar los períodos.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    title="Generar períodos contables"
    subtitle="Cree un año completo, un rango de meses o meses específicos. Los meses ya existentes se omiten."
    size="md"
    :submit-label="newMonths.length ? `Generar ${newMonths.length} período(s)` : 'Generar'"
    :loading="saving"
    @update:model-value="emit('update:modelValue', $event)"
    @submit="submit"
  >
    <div class="ds-field">
      <label class="ds-field__label" for="gen-year">Año fiscal</label>
      <input
        id="gen-year"
        v-model.number="year"
        type="number"
        min="2000"
        max="2100"
        class="ds-input"
        style="max-width: 140px"
        required
      />
    </div>

    <div class="ds-field">
      <span class="ds-field__label">Modo de generación</span>
      <div class="ds-segmented" role="radiogroup">
        <label class="ds-segmented__option" :class="{ 'is-active': mode === 'FULL' }">
          <input v-model="mode" type="radio" value="FULL" /> Año completo
        </label>
        <label class="ds-segmented__option" :class="{ 'is-active': mode === 'RANGE' }">
          <input v-model="mode" type="radio" value="RANGE" /> Rango de meses
        </label>
        <label class="ds-segmented__option" :class="{ 'is-active': mode === 'MONTHS' }">
          <input v-model="mode" type="radio" value="MONTHS" /> Meses específicos
        </label>
      </div>
    </div>

    <div v-if="mode === 'RANGE'" class="ds-form-grid">
      <div class="ds-field">
        <label class="ds-field__label" for="gen-from">Desde</label>
        <select id="gen-from" v-model.number="startMonth" class="ds-input">
          <option v-for="(name, idx) in MONTH_NAMES_ES" :key="idx" :value="idx + 1">{{ name }}</option>
        </select>
      </div>
      <div class="ds-field">
        <label class="ds-field__label" for="gen-to">Hasta</label>
        <select id="gen-to" v-model.number="endMonth" class="ds-input">
          <option v-for="(name, idx) in MONTH_NAMES_ES" :key="idx" :value="idx + 1">{{ name }}</option>
        </select>
      </div>
    </div>

    <div v-if="mode === 'MONTHS' && yearValid" class="ds-field">
      <span class="ds-field__label">Seleccione los meses (los ya generados aparecen bloqueados)</span>
      <MonthGrid
        v-model="selectedMonths"
        mode="multi"
        :year="Number(year)"
        :periods="existingPeriods"
        :locked-months="existingMonths"
      />
    </div>

    <p
      class="ds-gen-preview"
      :class="{ 'is-warning': newMonths.length === 0 }"
    >
      {{ previewText }}
    </p>
    <p v-if="error" class="ds-field__error">{{ error }}</p>
  </FormModal>
</template>
