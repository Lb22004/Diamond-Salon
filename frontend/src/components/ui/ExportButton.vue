<script setup>
import { ref } from 'vue'
import http from '@/api/http'

const props = defineProps({
  book: {
    type: String,
    required: true, // e.g. 'journal', 'ledger', 'sales-fcf', 'purchases', 'chart'
  },
  params: {
    type: Object,
    default: () => ({}),
  },
  label: {
    type: String,
    default: 'Exportar',
  },
})

const emit = defineEmits(['exported', 'error'])
const open = ref(false)
const loadingFormat = ref('')

async function triggerExport(format) {
  open.value = false
  loadingFormat.value = format
  try {
    const response = await http.get(`/v1/exports/${props.book}/`, {
      params: { ...props.params, format },
      responseType: 'blob',
    })
    const ext = format === 'xlsx' ? 'xlsx' : 'pdf'
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `diamond-salon-${props.book}.${ext}`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    emit('exported', { book: props.book, format })
  } catch (err) {
    emit('error', err)
  } finally {
    loadingFormat.value = ''
  }
}
</script>

<template>
  <div class="ds-export-dropdown">
    <button
      type="button"
      class="ds-btn ds-btn--outline ds-export-dropdown__trigger"
      :disabled="Boolean(loadingFormat)"
      @click="open = !open"
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
      </svg>
      <span v-if="loadingFormat">Generando {{ loadingFormat.toUpperCase() }}…</span>
      <span v-else>{{ label }}</span>
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        style="opacity: 0.65"
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </button>
    <div v-if="open" class="ds-export-dropdown__menu">
      <button type="button" class="ds-export-dropdown__item" @click="triggerExport('pdf')">
        <span>Documento PDF (Formato Legal)</span>
      </button>
      <button type="button" class="ds-export-dropdown__item" @click="triggerExport('xlsx')">
        <span>Hoja de Cálculo Excel (.xlsx)</span>
      </button>
    </div>
  </div>
</template>
