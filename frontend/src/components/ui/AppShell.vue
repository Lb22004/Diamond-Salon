<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePeriodStore } from '@/stores/period'
import http from '@/api/http'
import Badge from './Badge.vue'
import PeriodPicker from './PeriodPicker.vue'
import GlobalSearchModal from './GlobalSearchModal.vue'

const authStore = useAuthStore()
const periodStore = usePeriodStore()
const router = useRouter()

const searchOpen = ref(false)
const notifOpen = ref(false)
const notifications = ref([])

const coreMenu = [
  { to: '/panel', name: 'panel', label: 'Panel', code: '00' },
  { to: '/catalogo-cuentas', name: 'catalogo', label: 'Catálogo de cuentas', code: '01' },
  { to: '/inventario', name: 'inventario', label: 'Inventario mixto', code: '02' },
  { to: '/libro-ventas', name: 'ventas', label: 'Libro de ventas', code: '03' },
  { to: '/libro-compras', name: 'compras', label: 'Libro de compras', code: '04' },
  { to: '/libro-diario', name: 'diario', label: 'Libro diario', code: '05' },
  { to: '/libro-mayor', name: 'mayor', label: 'Libro mayor', code: '06' },
]

const adminMenu = [
  { to: '/usuarios', name: 'usuarios', label: 'Usuarios y roles', roles: ['ADMIN'] },
  {
    to: '/configuracion',
    name: 'configuracion',
    label: 'Empresa, Períodos y Auditoría',
    roles: ['ADMIN', 'ACCOUNTANT', 'AUDITOR'],
  },
]

const visibleCoreMenu = computed(() =>
  coreMenu.filter((item) => authStore.canAccessRoute(item.name))
)

const visibleAdminMenu = computed(() =>
  adminMenu.filter((item) => item.roles.includes(authStore.role))
)

async function fetchNotifications() {
  if (!authStore.isAuthenticated) return
  try {
    const { data } = await http.get('/v1/notifications/')
    notifications.value = data.items || []
  } catch {
    notifications.value = []
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function goToNotification(item) {
  notifOpen.value = false
  if (item.to) router.push(item.to)
}

onMounted(async () => {
  if (authStore.isAuthenticated) {
    await Promise.all([
      authStore.fetchMe(),
      periodStore.fetchPeriods(),
      fetchNotifications(),
    ])
  }
})
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand__diamond">◆</span>
        <div>
          Diamond Salón
          <small>ATELIER CONTABLE · NIIF PYMES</small>
        </div>
      </div>

      <p class="section">LIBROS &amp; OPERACIONES</p>
      <nav class="sidebar__nav">
        <RouterLink
          v-for="item in visibleCoreMenu"
          :key="item.to"
          :to="item.to"
          class="sidebar__link"
        >
          <span class="sidebar__code">{{ item.code }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <template v-if="visibleAdminMenu.length">
        <p class="section" style="margin-top: 1.5rem">PLATAFORMA &amp; CONTROL</p>
        <nav class="sidebar__nav">
          <RouterLink
            v-for="item in visibleAdminMenu"
            :key="item.to"
            :to="item.to"
            class="sidebar__link"
          >
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
      </template>

      <div class="sidebar__footer">
        <div class="sidebar__closing-box">
          <div class="sidebar__closing-label">CIERRE PERIÓDICO</div>
          <div class="sidebar__closing-period">{{ periodStore.periodLabel }}</div>
          <div class="sidebar__closing-status">
            <Badge :variant="periodStore.isPeriodOpen ? 'OPEN' : 'CLOSED'" size="sm">
              {{ periodStore.isPeriodOpen ? 'En curso · Abierto' : 'Período Cerrado' }}
            </Badge>
          </div>
          <RouterLink to="/libro-mayor" class="sidebar__closing-link">
            Ir a liquidación / cierre →
          </RouterLink>
        </div>
      </div>
    </aside>

    <div class="main-wrapper">
      <header class="topbar">
        <div class="topbar__left">
          <PeriodPicker />
        </div>

        <div class="topbar__right">
          <button
            type="button"
            class="topbar__search-btn"
            title="Búsqueda rápida (Ctrl+K)"
            @click="searchOpen = true"
          >
            <span>⌕ Buscar cuenta, partida o factura…</span>
            <kbd class="ds-kbd">Ctrl K</kbd>
          </button>

          <div class="topbar__notif-wrap">
            <button
              type="button"
              class="topbar__icon-btn"
              title="Notificaciones del sistema"
              @click="notifOpen = !notifOpen"
            >
              🔔
              <span v-if="notifications.length" class="topbar__notif-badge">
                {{ notifications.length }}
              </span>
            </button>

            <div v-if="notifOpen" class="topbar__notif-menu">
              <div class="topbar__notif-header">Alertas contables y operativas</div>
              <div v-if="notifications.length === 0" class="topbar__notif-empty">
                Sin alertas pendientes en este período.
              </div>
              <button
                v-for="n in notifications"
                :key="n.id"
                type="button"
                class="topbar__notif-item"
                @click="goToNotification(n)"
              >
                <Badge :variant="n.level" size="sm">{{ n.level.toUpperCase() }}</Badge>
                <div>
                  <div class="topbar__notif-title">{{ n.title }}</div>
                  <div class="topbar__notif-detail">{{ n.detail }}</div>
                </div>
              </button>
            </div>
          </div>

          <div class="topbar__user">
            <div class="topbar__user-info">
              <span class="topbar__user-name">{{ authStore.displayName }}</span>
              <Badge :variant="authStore.role" size="sm">{{ authStore.roleLabel }}</Badge>
            </div>
            <button
              type="button"
              class="ds-btn ds-btn--sm ds-btn--outline"
              title="Cerrar sesión"
              @click="handleLogout"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      <main class="content">
        <slot />
      </main>
    </div>

    <GlobalSearchModal v-model="searchOpen" />
  </div>
</template>
