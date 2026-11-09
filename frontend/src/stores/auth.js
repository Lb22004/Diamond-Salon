import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import http from '@/api/http'

const ROLE_LABELS = {
  ADMIN: 'Administrador',
  ACCOUNTANT: 'Contador / Auditor líder',
  AUDITOR: 'Auditor',
  PURCHASING: 'Compras y almacén',
  CASHIER: 'Caja / recepción',
  READONLY: 'Solo lectura',
}

const DEFAULT_VIEWS_BY_ROLE = {
  ADMIN: ['panel', 'catalogo', 'inventario', 'ventas', 'compras', 'diario', 'mayor', 'usuarios', 'configuracion'],
  ACCOUNTANT: ['panel', 'catalogo', 'inventario', 'ventas', 'compras', 'diario', 'mayor', 'configuracion'],
  AUDITOR: ['panel', 'catalogo', 'inventario', 'ventas', 'compras', 'diario', 'mayor', 'configuracion'],
  PURCHASING: ['panel', 'inventario', 'compras'],
  CASHIER: ['panel', 'inventario', 'ventas'],
  READONLY: ['panel', 'catalogo', 'inventario', 'ventas', 'compras', 'diario', 'mayor'],
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user_profile') || 'null'))
  const company = ref(null)
  const loading = ref(false)
  const error = ref('')

  const isAuthenticated = computed(() => Boolean(accessToken.value))
  const role = computed(() => user.value?.role || 'READONLY')
  const roleLabel = computed(() => user.value?.role_label || ROLE_LABELS[role.value] || role.value)
  const displayName = computed(
    () => user.value?.full_display_name || user.value?.username || 'Invitado'
  )
  const isAdmin = computed(() => role.value === 'ADMIN')
  const isAccountant = computed(() => role.value === 'ADMIN' || role.value === 'ACCOUNTANT')
  const canViewAudit = computed(() => ['ADMIN', 'AUDITOR', 'ACCOUNTANT'].includes(role.value))
  const allowedViews = computed(
    () => user.value?.permissions?.views || DEFAULT_VIEWS_BY_ROLE[role.value] || ['panel']
  )

  async function login(username, password) {
    loading.value = true
    error.value = ''
    try {
      const { data } = await http.post('/v1/auth/token/', { username, password })
      accessToken.value = data.access
      refreshToken.value = data.refresh
      user.value = data.user || { username, role: 'ADMIN' }

      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)
      localStorage.setItem('user_profile', JSON.stringify(user.value))
      return user.value
    } catch (err) {
      error.value =
        err.response?.data?.detail ||
        'Credenciales inválidas. Verifique su usuario y contraseña.'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    if (!accessToken.value) return null
    try {
      const { data } = await http.get('/v1/auth/me/')
      if (data.user) {
        user.value = data.user
        localStorage.setItem('user_profile', JSON.stringify(data.user))
      }
      if (data.company) {
        company.value = data.company
      }
      return data
    } catch (err) {
      if (err.response?.status === 401) {
        logout()
      }
      return null
    }
  }

  function logout() {
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_profile')
  }

  function canAccessRoute(routeName) {
    if (!routeName || routeName === 'login') return true
    if (!isAuthenticated.value) return false
    if (role.value === 'ADMIN') return true
    return allowedViews.value.includes(routeName)
  }

  return {
    accessToken,
    refreshToken,
    user,
    company,
    loading,
    error,
    isAuthenticated,
    role,
    roleLabel,
    displayName,
    isAdmin,
    isAccountant,
    canViewAudit,
    allowedViews,
    login,
    fetchMe,
    logout,
    canAccessRoute,
  }
})
