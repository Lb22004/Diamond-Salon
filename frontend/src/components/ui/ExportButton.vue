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
      class="ds-btn ds-btn--outline"
      :disabled="Boolean(loadingFormat)"
      @click="open = !open"
    >
      <span v-if="loadingFormat">Generando {{ loadingFormat.toUpperCase() }}…</span>
      <span v-else>⇩ {{ label }} ▾</span>
    </button>
    <div v-if="open" class="ds-export-dropdown__menu">
      <button type="button" class="ds-export-dropdown__item" @click="triggerExport('pdf')">
        Exportar PDF (Legal)
      </button>
      <button type="button" class="ds-export-dropdown__item" @click="triggerExport('xlsx')">
        Exportar Excel (.xlsx)
      </button>
    </div>
  </div>
</template>
