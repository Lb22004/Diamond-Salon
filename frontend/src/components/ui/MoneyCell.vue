<script setup>
import { computed } from 'vue'
import { formatMoney } from '@/utils/formatters'

const props = defineProps({
  value: {
    type: [String, Number],
    default: '0.00',
  },
  showSign: {
    type: Boolean,
    default: false,
  },
  mutedIfZero: {
    type: Boolean,
    default: true,
  },
  bold: {
    type: Boolean,
    default: false,
  },
})

const formatted = computed(() => formatMoney(props.value, { showSign: props.showSign }))
const isZero = computed(() => formatted.value === '$0.00' || formatted.value === '-$0.00')
const isNegative = computed(() => String(props.value ?? '').trim().startsWith('-'))
</script>

<template>
  <span
    class="ds-money"
    :class="{
      'ds-money--zero': mutedIfZero && isZero,
      'ds-money--negative': isNegative && !isZero,
      'ds-money--bold': bold,
    }"
  >
    {{ formatted }}
  </span>
</template>
