<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePeriodStore } from '@/stores/period'
import Badge from '@/components/ui/Badge.vue'

const authStore = useAuthStore()
const periodStore = usePeriodStore()
const router = useRouter()
const route = useRoute()

const username = ref('admin')
const password = ref('diamond2026')
const localError = ref('')

const demoAccounts = [
  { user: 'admin', label: 'Maira · ADMIN', role: 'ADMIN' },
  { user: 'contador', label: 'Jose Roberto · CONTADOR', role: 'ACCOUNTANT' },
  { user: 'auditor', label: 'Ferdinand · AUDITOR', role: 'AUDITOR' },
  { user: 'compras', label: 'Víctor · COMPRAS', role: 'PURCHASING' },
  { user: 'cajero', label: 'Valeria · CAJA', role: 'CASHIER' },
  { user: 'lectura', label: 'Gerencia · LECTURA', role: 'READONLY' },
]

function fillDemo(account) {
  username.value = account.user
  password.value = 'diamond2026'
  localError.value = ''
}

async function handleSubmit() {
  localError.value = ''
  if (!username.value.trim() || !password.value) {
    localError.value = 'Ingrese su nombre de usuario y contraseña.'
    return
  }
  try {
    await authStore.login(username.value.trim(), password.value)
    await periodStore.fetchPeriods()
    const redirectPath = route.query.redirect || '/panel'
    router.push(String(redirectPath))
  } catch {
    localError.value = authStore.error
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-card__brand">
        <span class="login-card__diamond">◆</span>
        <div>
          <h1>Diamond Salón</h1>
          <p>ATELIER CONTABLE · SISTEMA INTEGRAL NIIF PYMES</p>
        </div>
      </div>

      <form class="login-card__form" @submit.prevent="handleSubmit">
        <div class="ds-field">
          <label class="ds-field__label" for="login-username">Usuario</label>
          <input
            id="login-username"
            v-model="username"
            type="text"
            class="ds-input"
            autocomplete="username"
            placeholder="Ej. admin, contador, compras…"
            required
          />
        </div>

        <div class="ds-field">
          <label class="ds-field__label" for="login-password">Contraseña</label>
          <input
            id="login-password"
            v-model="password"
            type="password"
            class="ds-input"
            autocomplete="current-password"
            placeholder="••••••••"
            required
          />
        </div>

        <p v-if="localError" class="ds-alert ds-alert--danger">{{ localError }}</p>

        <button
          type="submit"
          class="ds-btn ds-btn--primary ds-btn--block"
          :disabled="authStore.loading"
        >
          {{ authStore.loading ? 'Autenticando…' : 'Iniciar sesión en el Atelier' }}
        </button>
      </form>

      <div class="login-card__demo">
        <p class="login-card__demo-title">Perfiles de demostración por rol (contraseña: <code>diamond2026</code>):</p>
        <div class="login-card__demo-grid">
          <button
            v-for="acc in demoAccounts"
            :key="acc.user"
            type="button"
            class="login-card__demo-chip"
            :class="{ 'is-selected': username === acc.user }"
            @click="fillDemo(acc)"
          >
            <span>{{ acc.label }}</span>
            <Badge :variant="acc.role" size="sm">{{ acc.role }}</Badge>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
