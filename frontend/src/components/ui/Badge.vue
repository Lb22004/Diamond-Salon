<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'neutral',
  },
  label: {
    type: String,
    default: '',
  },
  size: {
    type: String,
    default: 'md', // 'sm' | 'md'
  },
})

const VARIANT_MAP = {
  VITRINA: 'badge-wine',
  SALE: 'badge-wine',
  CABINA: 'badge-gold',
  SERVICE: 'badge-gold',
  OPEN: 'badge-success',
  POSTED: 'badge-success',
  ISSUED: 'badge-success',
  OK: 'badge-success',
  CLOSED: 'badge-ink',
  DRAFT: 'badge-warning',
  WARNING: 'badge-warning',
  PENDING: 'badge-warning',
  REVERSED: 'badge-danger',
  VOIDED: 'badge-danger',
  DANGER: 'badge-danger',
  CRITICAL: 'badge-danger',
  ADMIN: 'badge-wine',
  ACCOUNTANT: 'badge-gold',
  AUDITOR: 'badge-ink',
  PURCHASING: 'badge-info',
  CASHIER: 'badge-success',
  READONLY: 'badge-neutral',
  wine: 'badge-wine',
  gold: 'badge-gold',
  ink: 'badge-ink',
  success: 'badge-success',
  warning: 'badge-warning',
  danger: 'badge-danger',
  info: 'badge-info',
  neutral: 'badge-neutral',
}

const badgeClass = computed(() => {
  const key = props.variant || 'neutral'
  return [
    'ds-badge',
    `ds-badge--${props.size}`,
    VARIANT_MAP[key] || VARIANT_MAP[key.toUpperCase()] || 'badge-neutral',
  ]
})
</script>

<template>
  <span :class="badgeClass">
    <slot>{{ label }}</slot>
  </span>
</template>
