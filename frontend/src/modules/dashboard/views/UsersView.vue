<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '@/api/http'
import { Badge, DataTable, FormModal, SearchInput } from '@/components/ui'
import { formatDateShort } from '@/utils/formatters'

const users = ref([])
const loading = ref(false)
const searchQuery = ref('')
const roleFilter = ref('')

const modalOpen = ref(false)
const saving = ref(false)
const formError = ref('')
const editingId = ref(null)

const form = ref({
  username: '',
  first_name: '',
  last_name: '',
  email: '',
  role: 'READONLY',
  password: '',
  is_active: true,
})

const roleOptions = [
  { value: 'ADMIN', label: 'ADMIN · Administrador del sistema' },
  { value: 'ACCOUNTANT', label: 'ACCOUNTANT · Contador / Auditor líder' },
  { value: 'AUDITOR', label: 'AUDITOR · Auditor externo (Solo lectura + bitácora)' },
  { value: 'PURCHASING', label: 'PURCHASING · Compras y almacén' },
  { value: 'CASHIER', label: 'CASHIER · Caja / recepción' },
  { value: 'READONLY', label: 'READONLY · Gerencia / Solo lectura' },
]

const columns = [
  { key: 'username', label: 'Usuario', sortable: true },
  { key: 'full_display_name', label: 'Nombre completo', sortable: true },
  { key: 'email', label: 'Correo electrónico' },
  { key: 'role', label: 'Rol asignado', sortable: true },
  { key: 'is_active', label: 'Estado', align: 'center' },
  { key: 'date_joined', label: 'Alta', type: 'date' },
  { key: 'actions', label: 'Acciones', align: 'right' },
]

const filteredUsers = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return users.value.filter((u) => {
    if (roleFilter.value && u.role !== roleFilter.value) return false
    if (!q) return true
    return (
      u.username?.toLowerCase().includes(q) ||
      u.full_display_name?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q)
    )
  })
})

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await http.get('/v1/users/')
    users.value = Array.isArray(data) ? data : data.results || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  formError.value = ''
  form.value = {
    username: '',
    first_name: '',
    last_name: '',
    email: '',
    role: 'CASHIER',
    password: '',
    is_active: true,
  }
  modalOpen.value = true
}

function openEdit(row) {
  editingId.value = row.id
  formError.value = ''
  form.value = {
    username: row.username,
    first_name: row.first_name || '',
    last_name: row.last_name || '',
    email: row.email || '',
    role: row.role,
    password: '',
    is_active: row.is_active,
  }
  modalOpen.value = true
}

async function saveUser() {
  saving.value = true
  formError.value = ''
  try {
    const payload = {
      username: form.value.username.trim(),
      first_name: form.value.first_name.trim(),
      last_name: form.value.last_name.trim(),
      email: form.value.email.trim(),
      role: form.value.role,
      is_active: form.value.is_active,
    }
    if (form.value.password) {
      payload.password = form.value.password
    }
    if (editingId.value) {
      await http.patch(`/v1/users/${editingId.value}/`, payload)
    } else {
      await http.post('/v1/users/', payload)
    }
    modalOpen.value = false
    await fetchUsers()
  } catch (err) {
    const detail = err.response?.data
    formError.value =
      typeof detail === 'object'
        ? Object.values(detail).flat().join(' ')
        : 'No se pudo guardar el usuario.'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <section class="ds-page">
    <header class="ds-page__header">
      <div>
        <div class="ds-page__eyebrow">SEGURIDAD &amp; CONTROL DE ACCESO (RF-SEG-04)</div>
        <h1 class="ds-page__title">Usuarios y Roles del Sistema</h1>
      </div>
      <div class="ds-page__actions">
        <button type="button" class="ds-btn ds-btn--primary" @click="openCreate">
          + Nuevo usuario
        </button>
      </div>
    </header>

    <DataTable :columns="columns" :rows="filteredUsers" :loading="loading">
      <template #toolbar>
        <div class="ds-toolbar">
          <SearchInput
            v-model="searchQuery"
            placeholder="Buscar por usuario, nombre o correo…"
          />
          <select v-model="roleFilter" class="ds-input ds-input--sm" style="max-width: 240px">
            <option value="">Todos los roles</option>
            <option v-for="r in roleOptions" :key="r.value" :value="r.value">
              {{ r.label }}
            </option>
          </select>
        </div>
      </template>

      <template #cell-username="{ value }">
        <strong>{{ value }}</strong>
      </template>

      <template #cell-role="{ row }">
        <Badge :variant="row.role" size="sm">{{ row.role_label || row.role }}</Badge>
      </template>

      <template #cell-is_active="{ value }">
        <Badge :variant="value ? 'OK' : 'CLOSED'" size="sm">
          {{ value ? 'Activo' : 'Inactivo' }}
        </Badge>
      </template>

      <template #cell-date_joined="{ value }">
        {{ formatDateShort(value) }}
      </template>

      <template #cell-actions="{ row }">
        <button type="button" class="ds-btn ds-btn--sm ds-btn--outline" @click="openEdit(row)">
          Editar
        </button>
      </template>
    </DataTable>

    <FormModal
      v-model="modalOpen"
      :title="editingId ? 'Editar usuario y rol' : 'Registrar nuevo usuario'"
      subtitle="Asigne el rol según la matriz de segregación de funciones del SRS §2.3"
      :loading="saving"
      @submit="saveUser"
    >
      <div class="ds-form-grid">
        <div class="ds-field">
          <label class="ds-field__label">Nombre de usuario *</label>
          <input v-model="form.username" type="text" class="ds-input" required />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Rol del sistema *</label>
          <select v-model="form.role" class="ds-input" required>
            <option v-for="r in roleOptions" :key="r.value" :value="r.value">
              {{ r.label }}
            </option>
          </select>
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Nombres</label>
          <input v-model="form.first_name" type="text" class="ds-input" />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Apellidos</label>
          <input v-model="form.last_name" type="text" class="ds-input" />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">Correo electrónico</label>
          <input v-model="form.email" type="email" class="ds-input" />
        </div>

        <div class="ds-field">
          <label class="ds-field__label">
            {{ editingId ? 'Nueva contraseña (opcional)' : 'Contraseña inicial *' }}
          </label>
          <input
            v-model="form.password"
            type="password"
            class="ds-input"
            :required="!editingId"
            minlength="6"
            placeholder="Mínimo 6 caracteres"
          />
        </div>
      </div>

      <label class="ds-checkbox">
        <input v-model="form.is_active" type="checkbox" />
        <span>Cuenta activa (permite iniciar sesión)</span>
      </label>

      <p v-if="formError" class="ds-alert ds-alert--danger">{{ formError }}</p>
    </FormModal>
  </section>
</template>
