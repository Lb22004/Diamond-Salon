<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import http from '@/api/http'
import Badge from './Badge.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])
const router = useRouter()
const query = ref('')
const results = ref([])
const selectedIndex = ref(0)
const inputRef = ref(null)
let debounceTimer = null

const FALLBACK_VIEWS = [
  { title: 'Panel Principal (Dashboard)', subtitle: 'KPIs del período y resumen general', to: '/panel', category: 'VISTA' },
  { title: 'Catálogo de cuentas', subtitle: 'Vista 1 · Plan de cuentas NIIF PYMES', to: '/catalogo-cuentas', category: 'VISTA' },
  { title: 'Inventario mixto', subtitle: 'Vista 2 · Vitrina (Venta) y Cabina (Servicio)', to: '/inventario', category: 'VISTA' },
  { title: 'Libro de ventas', subtitle: 'Vista 3 · FCF y CCF emitidos', to: '/libro-ventas', category: 'VISTA' },
  { title: 'Libro de compras', subtitle: 'Vista 4 · Compras CCF y crédito fiscal', to: '/libro-compras', category: 'VISTA' },
  { title: 'Libro diario', subtitle: 'Vista 5 · Partidas y asientos contables', to: '/libro-diario', category: 'VISTA' },
  { title: 'Libro mayor', subtitle: 'Vista 6 · Mayorización, saldos y cierre mensual', to: '/libro-mayor', category: 'VISTA' },
  { title: 'Usuarios y Roles', subtitle: 'Administración de usuarios RBAC', to: '/usuarios', category: 'ADMIN' },
  { title: 'Configuración y Bitácora', subtitle: 'Empresa, períodos y auditoría', to: '/configuracion', category: 'ADMIN' },
]

async function runSearch(term) {
  try {
    const { data } = await http.get('/v1/search/', { params: { q: term } })
    results.value = data.results || []
  } catch {
    const q = term.toLowerCase()
    results.value = FALLBACK_VIEWS.filter(
      (v) => !q || v.title.toLowerCase().includes(q) || v.subtitle.toLowerCase().includes(q)
    )
  }
  selectedIndex.value = 0
}

watch(
  () => props.modelValue,
  async (open) => {
    if (open) {
      query.value = ''
      await runSearch('')
      await nextTick()
      inputRef.value?.focus()
    }
  }
)

function onInput(event) {
  query.value = event.target.value
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    runSearch(query.value)
  }, 150)
}

function close() {
  emit('update:modelValue', false)
}

function selectItem(item) {
  if (!item) return
  close()
  router.push(item.to)
}

function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    emit('update:modelValue', !props.modelValue)
    return
  }
  if (!props.modelValue) return
  if (e.key === 'Escape') {
    close()
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (results.value.length) {
      selectedIndex.value = (selectedIndex.value + 1) % results.value.length
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (results.value.length) {
      selectedIndex.value =
        (selectedIndex.value - 1 + results.value.length) % results.value.length
    }
  } else if (e.key === 'Enter' && results.value[selectedIndex.value]) {
    e.preventDefault()
    selectItem(results.value[selectedIndex.value])
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="ds-modal-backdrop" @click.self="close">
      <div class="ds-cmd-palette" role="dialog" aria-label="Búsqueda global">
        <div class="ds-cmd-palette__search">
          <span class="ds-cmd-palette__icon">⌕</span>
          <input
            ref="inputRef"
            type="text"
            :value="query"
            placeholder="Buscar cuenta (110101), partida, factura (FCF-0012) o vista…"
            class="ds-cmd-palette__input"
            @input="onInput"
          />
          <kbd class="ds-kbd" @click="close">ESC</kbd>
        </div>

        <ul class="ds-cmd-palette__list">
          <li v-if="results.length === 0" class="ds-cmd-palette__empty">
            Sin resultados para «{{ query }}»
          </li>
          <li
            v-for="(item, idx) in results"
            :key="`${item.category}-${item.to}-${idx}`"
            class="ds-cmd-palette__item"
            :class="{ 'is-active': idx === selectedIndex }"
            @mouseenter="selectedIndex = idx"
            @click="selectItem(item)"
          >
            <div>
              <div class="ds-cmd-palette__title">{{ item.title }}</div>
              <div class="ds-cmd-palette__subtitle">{{ item.subtitle }}</div>
            </div>
            <Badge
              :variant="
                item.category === 'CUENTA'
                  ? 'gold'
                  : item.category === 'DOCUMENTO'
                    ? 'wine'
                    : 'neutral'
              "
              size="sm"
            >
              {{ item.category }}
            </Badge>
          </li>
        </ul>
      </div>
    </div>
  </Teleport>
</template>
