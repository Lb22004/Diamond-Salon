import { createRouter, createWebHistory } from 'vue-router'

// Each module owns its folder under src/modules/<module>/ (see docs/IMPLEMENTATION_PLAN.md)
const routes = [
  { path: '/', redirect: '/panel' },
  { path: '/panel', name: 'panel', meta: { title: 'Panel' }, component: () => import('@/modules/dashboard/views/PanelView.vue') },
  { path: '/catalogo-cuentas', name: 'catalogo', meta: { title: 'Catálogo de cuentas' }, component: () => import('@/modules/accounting/views/CatalogoCuentasView.vue') },
  { path: '/inventario', name: 'inventario', meta: { title: 'Inventario' }, component: () => import('@/modules/inventory/views/InventarioMixtoView.vue') },
  { path: '/libro-ventas', name: 'ventas', meta: { title: 'Libro de ventas' }, component: () => import('@/modules/sales/views/LibroVentasView.vue') },
  { path: '/libro-compras', name: 'compras', meta: { title: 'Libro de compras' }, component: () => import('@/modules/purchases/views/LibroComprasView.vue') },
  { path: '/libro-diario', name: 'diario', meta: { title: 'Libro diario' }, component: () => import('@/modules/accounting/views/LibroDiarioView.vue') },
  { path: '/libro-mayor', name: 'mayor', meta: { title: 'Libro mayor' }, component: () => import('@/modules/reports/views/LibroMayorView.vue') },
]

export default createRouter({ history: createWebHistory(), routes })
