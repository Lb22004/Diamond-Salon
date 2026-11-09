<script setup>
import { computed } from 'vue'
import { formatMoney } from '@/utils/formatters'
import Badge from './Badge.vue'

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  value: {
    type: [String, Number],
    default: '0.00',
  },
  isCurrency: {
    type: Boolean,
    default: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  badge: {
    type: String,
    default: '',
  },
  badgeVariant: {
    type: String,
    default: 'neutral',
  },
  tone: {
    type: String,
    default: 'default', // 'default' | 'wine' | 'gold' | 'ink' | 'danger'
  },
})

const displayValue = computed(() =>
  props.isCurrency ? formatMoney(props.value) : String(props.value ?? '0')
)
</script>

<template>
  <article class="ds-kpi-card" :class="`ds-kpi-card--${tone}`">
    <header class="ds-kpi-card__header">
      <span class="ds-kpi-card__title">{{ title }}</span>
      <Badge v-if="badge" :variant="badgeVariant" size="sm">{{ badge }}</Badge>
    </header>
    <div class="ds-kpi-card__value">
      <slot name="value">{{ displayValue }}</slot>
    </div>
    <footer v-if="subtitle || $slots.footer" class="ds-kpi-card__footer">
      <slot name="footer">{{ subtitle }}</slot>
    </footer>
  </article>
</template>
