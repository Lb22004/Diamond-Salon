import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Each module owns its folder under src/modules/<module>/ (see docs/IMPLEMENTATION_PLAN.md)
const routes = [
  { path: '/', redirect: '/panel' },
  {
    path: '/login',
    name: 'login',
    meta: { title: 'Iniciar sesión', guest: true },
    component: () => import('@/modules/dashboard/views/LoginView.vue'),
  },
  {
    path: '/panel',
    name: 'panel',
    meta: { title: 'Panel' },
    component: () => import('@/modules/dashboard/views/PanelView.vue'),
  },
  {
    path: '/catalogo-cuentas',
    name: 'catalogo',
    meta: { title: 'Catálogo de cuentas' },
    component: () => import('@/modules/accounting/views/CatalogoCuentasView.vue'),
  },
  {
    path: '/inventario',
    name: 'inventario',
    meta: { title: 'Inventario' },
    component: () => import('@/modules/inventory/views/InventarioMixtoView.vue'),
  },
  {
    path: '/libro-ventas',
    name: 'ventas',
    meta: { title: 'Libro de ventas' },
    component: () => import('@/modules/sales/views/LibroVentasView.vue'),
  },
  {
    path: '/libro-compras',
    name: 'compras',
    meta: { title: 'Libro de compras' },
    component: () => import('@/modules/purchases/views/LibroComprasView.vue'),
  },
  {
    path: '/libro-diario',
    name: 'diario',
    meta: { title: 'Libro diario' },
    component: () => import('@/modules/accounting/views/LibroDiarioView.vue'),
  },
  {
    path: '/libro-mayor',
    name: 'mayor',
    meta: { title: 'Libro mayor' },
    component: () => import('@/modules/reports/views/LibroMayorView.vue'),
  },
  {
    path: '/usuarios',
    name: 'usuarios',
    meta: { title: 'Usuarios y roles', roles: ['ADMIN'] },
    component: () => import('@/modules/dashboard/views/UsersView.vue'),
  },
  {
    path: '/configuracion',
    name: 'configuracion',
    meta: { title: 'Configuración y Auditoría', roles: ['ADMIN', 'ACCOUNTANT', 'AUDITOR'] },
    component: () => import('@/modules/dashboard/views/CompanySettingsView.vue'),
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  document.title = to.meta?.title
    ? `${to.meta.title} · Diamond Salón`
    : 'Diamond Salón · Atelier Contable'

  const authStore = useAuthStore()
  if (to.meta?.guest) {
    if (authStore.isAuthenticated) {
      return { path: '/panel' }
    }
    return true
  }

  if (!authStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.meta?.roles && !to.meta.roles.includes(authStore.role)) {
    return { path: '/panel' }
  }

  if (!authStore.canAccessRoute(String(to.name || ''))) {
    return { path: '/panel' }
  }

  return true
})

export default router
