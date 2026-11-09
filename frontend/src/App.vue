<script setup>
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppShell from '@/components/ui/AppShell.vue'

const route = useRoute()
const isGuestLayout = computed(() => Boolean(route.meta?.guest))
</script>

<template>
  <RouterView v-if="isGuestLayout" />
  <AppShell v-else>
    <RouterView />
  </AppShell>
</template>
