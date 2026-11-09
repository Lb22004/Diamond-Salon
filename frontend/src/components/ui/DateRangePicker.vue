<script setup>
import { formatDateLong } from '@/utils/formatters'

const props = defineProps({
  from: {
    type: String,
    default: '',
  },
  to: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:from', 'update:to', 'change'])

function updateFrom(e) {
  const val = e.target.value
  emit('update:from', val)
  emit('change', { from: val, to: props.to })
}

function updateTo(e) {
  const val = e.target.value
  emit('update:to', val)
  emit('change', { from: props.from, to: val })
}

function clearDates() {
  emit('update:from', '')
  emit('update:to', '')
  emit('change', { from: '', to: '' })
}
</script>

<template>
  <div class="ds-date-range">
    <label class="ds-date-range__field">
      <span class="ds-date-range__label">Desde</span>
      <input type="date" class="ds-input ds-input--sm" :value="from" @input="updateFrom" />
    </label>
    <label class="ds-date-range__field">
      <span class="ds-date-range__label">Hasta</span>
      <input type="date" class="ds-input ds-input--sm" :value="to" @input="updateTo" />
    </label>
    <span v-if="from || to" class="ds-date-range__preview">
      {{ formatDateLong(from) }} – {{ formatDateLong(to) }}
      <button type="button" class="ds-btn-link" @click="clearDates">Limpiar</button>
    </span>
  </div>
</template>
