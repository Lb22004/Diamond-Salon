<script setup>
import { onMounted, ref } from 'vue'
import http from '@/api/http'

const health = ref({ status: 'checking…' })

onMounted(async () => {
  try {
    const { data } = await http.get('/health/')
    health.value = data
  } catch (err) {
    health.value = { status: 'error', detail: err.message }
  }
})
</script>

<template>
  <section>
    <h1>Panel</h1>
    <div class="placeholder">
      <p><strong>Backend:</strong> {{ health.status }}</p>
      <p v-if="health.database"><strong>Base de datos:</strong> {{ health.database }}</p>
      <p v-if="health.detail"><strong>Detalle:</strong> {{ health.detail }}</p>
      <p>Owner: P1 (Plataforma). KPIs del período — ver SRS RF-PAN.</p>
    </div>
  </section>
</template>
